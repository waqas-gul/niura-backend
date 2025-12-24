import numpy as np
from sqlalchemy.orm import Session
from app.schemas.eeg import EEGRecordIn
from typing import List

from app.events.kafka_producer import send_processed_eeg_event

# Import the EEG processing functions
from brainflow.data_filter import (
    DataFilter, FilterTypes, DetrendOperations, NoiseTypes
)
from brainflow.ml_model import (
    MLModel, BrainFlowModelParams,
    BrainFlowClassifiers, BrainFlowMetrics
)

from threading import Lock

class EEGService:
    _model = None  # Shared classifier instance
    _model_lock = Lock()  # Lock to ensure thread safety

    def __init__(self, db: Session=None):
        self.db = db
        self.FS = 250  # samples per second
        
    def filter_channel(self, arr):
        """Detrend → band-pass 5–50 Hz → notch 50 & 60 Hz → zero-mean."""
        d = arr.astype(float)
        DataFilter.detrend(d, DetrendOperations.LINEAR.value)
        DataFilter.perform_bandpass(d, self.FS, 5.0, 50.0, 4, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(d, self.FS, 49, 51, 4, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.remove_environmental_noise(d, self.FS, NoiseTypes.FIFTY.value)
        DataFilter.remove_environmental_noise(d, self.FS, NoiseTypes.SIXTY.value)
        return d - np.mean(d)

    @classmethod
    def get_model(cls):
        """Ensure a single classifier instance is prepared."""
        with cls._model_lock:
            if cls._model is None:
                params = BrainFlowModelParams(
                    BrainFlowMetrics.MINDFULNESS.value,
                    BrainFlowClassifiers.DEFAULT_CLASSIFIER.value
                )
                cls._model = MLModel(params)
                cls._model.prepare()
            return cls._model

    def compute_metrics(self, segment, model):
        """
        1) Apply the GUI's second-pass filter (1.5–45 Hz) with per-channel .copy()
        2) Get avg/std band powers → feature vector → concentration
        3) relaxation = 1 – concentration
        4) stress = β / (α + β), wellness = concentration
        5) ROUND all four metrics to **3** decimals
        """
        # ─── EXTRA GUI FILTER (copy each channel) ──────────────────────────────────
        wf = np.zeros_like(segment, dtype=np.float64)
        for ch in range(segment.shape[1]):
            arr = segment[:, ch].astype(np.float64).copy()
            DataFilter.detrend(arr, DetrendOperations.LINEAR.value)
            DataFilter.perform_bandpass(arr, self.FS, 1.5, 45.0, 4,
                                        FilterTypes.BUTTERWORTH.value, 0)
            wf[:, ch] = arr

        # feature vector & concentration
        try:
            data_t = np.ascontiguousarray(wf.T, dtype=np.float64)
            avg_bp, std_bp = DataFilter.get_avg_band_powers(
                data_t, list(range(data_t.shape[0])), self.FS, True
            )
            feat = np.concatenate((avg_bp, std_bp))
            conc = float(model.predict(feat)[0])
        except Exception:
            conc = 0.0
            avg_bp = [0, 0, 0, 0, 0]

        relax = 1.0 - conc

        # stress = β / (α + β)
        alpha, beta = avg_bp[2], avg_bp[3]
        stress = beta / (alpha + beta) if (alpha + beta) > 0 else 0.0

        wellness = conc

        # ─── ROUND TO 3 DECIMALS ────────────────────────────────────────────────────
        conc = round(conc, 3)
        relax = round(relax, 3)
        stress = round(stress, 3)
        wellness = round(wellness, 3)
        # ───────────────────────────────────────────────────────────────────────────

        return conc, relax, stress, wellness

    def process_eeg_data(self, records: List[EEGRecordIn], duration: int = 4):
        """Process EEG data and return metrics for each record."""
        # Convert records to numpy array format
        times = [r.timestamp for r in records]
        eeg_data = np.array([r.eeg for r in records])
        
        # Apply initial GUI filter
        filt = np.apply_along_axis(self.filter_channel, 0, eeg_data)
        
        # Use the shared model
        model = self.get_model()

        # Calculate window parameters
        win = int(duration * self.FS)
        half = win // 2
        
        results = []
        
        for i, ts in enumerate(times):
            start = max(0, i - half)
            end = min(len(records), i + half)
            seg = filt[start:end, :]
            
            conc, relax, stress, wellness = self.compute_metrics(seg, model)
            
            results.append({
                'timestamp': ts,
                'concentration': conc,
                'relaxation': relax,
                'stress': stress,
                'wellness': wellness
            })
        
        return results

    def save_eeg_records(self, records: List[EEGRecordIn], user_id: int, duration: int = 4):
        # Process EEG data to get metrics
        metrics_results = self.process_eeg_data(records, duration)
        
        # Group records by second and calculate averages
        seconds_data = {}
        for i, record in enumerate(records):
            metrics = metrics_results[i]
            
            # Truncate timestamp to seconds (remove milliseconds)
            second_timestamp = record.timestamp.replace(microsecond=0)
            
            if second_timestamp not in seconds_data:
                seconds_data[second_timestamp] = {
                    'focus_values': [],
                    'stress_values': [],
                    'wellness_values': []
                }
            
            # Convert numpy types to Python native types and scale to desired ranges
            focus_value = float(metrics['concentration']) * 3.0 if metrics['concentration'] is not None else 0.0
            stress_value = float(metrics['stress']) * 3.0 if metrics['stress'] is not None else 0.0
            wellness_value = float(metrics['wellness']) * 100.0 if metrics['wellness'] is not None else 0.0
            
            seconds_data[second_timestamp]['focus_values'].append(focus_value)
            seconds_data[second_timestamp]['stress_values'].append(stress_value)
            seconds_data[second_timestamp]['wellness_values'].append(wellness_value)
        
        # Create database records with averaged values for each second
        processed_records = []
        for timestamp, data in seconds_data.items():
            # Calculate averages for each second
            avg_focus = sum(data['focus_values']) / len(data['focus_values']) if data['focus_values'] else 0.0
            avg_stress = sum(data['stress_values']) / len(data['stress_values']) if data['stress_values'] else 0.0
            avg_wellness = sum(data['wellness_values']) / len(data['wellness_values']) if data['wellness_values'] else 0.0
            
            processed_records.append({
                "timestamp": timestamp.isoformat(),
                "focus_label": avg_focus,
                "stress_label": avg_stress,
                "wellness_label": avg_wellness,
            })

        # Send all processed records to Kafka at once, outside the loop
        if processed_records:
            send_processed_eeg_event(user_id, processed_records)
    
        
        return len(processed_records)

   