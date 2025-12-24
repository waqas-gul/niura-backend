"""
FFT-based EEG Processing Service
Fast, lightweight alternative to BrainFlow-based processing
"""

import numpy as np
from scipy import signal
from scipy.integrate import simpson
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FFTEEGService:
    def __init__(self):
        # Configuration (matching fft_code/config.json)
        self.fs = 250  # Sample rate
        self.vref = 4.5
        self.gain = 24
        self.adc_bits = 24
        self.scale_factor = self._get_scale_factor()
        
        # Filter parameters
        self.bandpass_low = 0.5
        self.bandpass_high = 45.0
        self.bandpass_order = 4
        self.notch_freqs = [50.0, 100.0]
        self.notch_q = 30.0
        
        # Spectral analysis
        self.window_sec = 2.0
        self.overlap_ratio = 0.5
        
        # Band definitions
        self.bands = {
            'delta': [0.5, 4.0],
            'theta': [4.0, 8.0],
            'alpha': [8.0, 13.0],
            'beta': [13.0, 30.0],
            'gamma': [30.0, 45.0]
        }
        
        # Initialize filters
        self._init_filters()
    
    def _get_scale_factor(self) -> float:
        """Calculate ADC to microvolts conversion factor."""
        max_count = 2 ** (self.adc_bits - 1) - 1
        return (self.vref / self.gain / max_count) * 1e6
    
    def _init_filters(self):
        """Initialize bandpass and notch filters."""
        nyq = self.fs / 2
        low = self.bandpass_low / nyq
        high = self.bandpass_high / nyq
        self.bp_b, self.bp_a = signal.butter(self.bandpass_order, [low, high], btype='band')
        
        self.notch_coeffs = []
        for freq in self.notch_freqs:
            b, a = signal.iirnotch(freq, self.notch_q, self.fs)
            self.notch_coeffs.append((b, a))
    
    def _adc_to_uv(self, data: np.ndarray) -> np.ndarray:
        """Convert ADC counts to microvolts."""
        data_uv = data.astype(np.float64) * self.scale_factor
        # Remove DC offset
        data_uv -= np.mean(data_uv, axis=0, keepdims=True)
        return data_uv
    
    def _filter_data(self, data: np.ndarray) -> np.ndarray:
        """Apply bandpass and notch filters."""
        # Detrend
        data = signal.detrend(data, axis=0)
        # Bandpass
        data = signal.filtfilt(self.bp_b, self.bp_a, data, axis=0)
        # Notch filters
        for b, a in self.notch_coeffs:
            data = signal.filtfilt(b, a, data, axis=0)
        return data
    
    def _remove_artifacts(self, data: np.ndarray) -> np.ndarray:
        """Simple artifact removal using interpolation."""
        data = data.copy()
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        n_samples, n_channels = data.shape
        mask = np.zeros_like(data, dtype=bool)
        
        for ch in range(n_channels):
            ch_data = data[:, ch]
            # Amplitude-based artifact detection
            thresh = np.percentile(np.abs(ch_data), 99.5) * 1.5
            mask[:, ch] |= np.abs(ch_data) > thresh
            
            # Gradient-based detection
            grad = np.abs(np.diff(ch_data, prepend=ch_data[0]))
            grad_thresh = np.percentile(grad, 99.0) * 2.0
            mask[:, ch] |= grad > grad_thresh
            
            # Z-score based detection
            z = (ch_data - np.mean(ch_data)) / (np.std(ch_data) + 1e-10)
            mask[:, ch] |= np.abs(z) > 4.0
        
        # Interpolate bad samples
        for ch in range(n_channels):
            bad = np.where(mask[:, ch])[0]
            good = np.where(~mask[:, ch])[0]
            if len(bad) > 0 and len(good) > 0:
                data[bad, ch] = np.interp(bad, good, data[good, ch])
        
        return data
    
    def _compute_bandpowers(self, data: np.ndarray) -> Dict:
        """Compute absolute and relative band powers."""
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        
        nperseg = min(int(self.window_sec * self.fs), len(data))
        freqs, psd = signal.welch(data, fs=self.fs, nperseg=nperseg)
        freq_res = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
        total_power = simpson(psd, dx=freq_res)
        
        absolute, relative = {}, {}
        for band, (low, high) in self.bands.items():
            idx = (freqs >= low) & (freqs <= high)
            power = simpson(psd[idx], dx=freq_res) if np.any(idx) else 0.0
            absolute[band] = float(power)
            relative[band] = float(power / total_power) if total_power > 0 else 0.0
        
        dominant = max(relative, key=relative.get) if relative else 'unknown'
        return {'absolute': absolute, 'relative': relative, 'dominant': dominant}
    
    def _compute_metrics(self, bp: Dict) -> Dict:
        """Compute cognitive metrics from band powers."""
        def ratio(n, d):
            return n / (d + 1e-10)
        
        def scale_to_0_3(value, typical_range):
            """Scale value to 0-3 range to match bulk endpoint."""
            normalized = (value - typical_range[0]) / (typical_range[1] - typical_range[0])
            return float(np.clip(normalized * 3.0, 0, 3))
        
        def scale_to_0_100(value, typical_range):
            """Scale value to 0-100 range."""
            normalized = (value - typical_range[0]) / (typical_range[1] - typical_range[0])
            return float(np.clip(normalized * 100, 0, 100))
        
        # Calculate ratios
        high_beta = bp.get('high_beta', bp['beta'] * 0.5)
        focus_ratio = ratio(bp['beta'], bp['alpha'] + bp['theta'])
        stress_ratio = ratio(bp['beta'] + high_beta, bp['alpha'])
        readiness_ratio = ratio(bp['alpha'], bp['beta'] + high_beta)
        drowsiness_ratio = ratio(bp['theta'] + bp['delta'], bp['alpha'] + bp['beta'])
        engagement_ratio = focus_ratio  # Same as focus
        
        # Scale to match bulk endpoint (0-3 for focus/stress, 0-100 for wellness)
        return {
            'focus': scale_to_0_3(focus_ratio, [0.3, 2.5]),
            'stress': scale_to_0_3(stress_ratio, [0.5, 4.0]),
            'mental_readiness': scale_to_0_100(readiness_ratio, [0.2, 2.5]),
            'engagement': scale_to_0_100(engagement_ratio, [0.3, 2.5]),
            'drowsiness': scale_to_0_100(drowsiness_ratio, [0.3, 3.0]),
        }
    
    def process_eeg_records(self, records: List[Dict], duration: int = 2) -> List[Dict]:
        """
        Process EEG records and return metrics.
        
        Args:
            records: List of EEG records with 'eeg' field containing 4-channel data
            duration: Window duration in seconds
        
        Returns:
            List of processed records with metrics and band powers
        """
        try:
            # Convert records to numpy array
            eeg_data = np.array([r.eeg for r in records], dtype=np.int32)
            n_samples, n_channels = eeg_data.shape
            
            logger.info(f"Processing {n_samples} samples, {n_channels} channels with FFT pipeline")
            
            # Step 1: Convert to microvolts
            data_uv = self._adc_to_uv(eeg_data)
            
            # Step 2: Filter
            data_filt = self._filter_data(data_uv)
            
            # Step 3: Remove artifacts
            data_clean = self._remove_artifacts(data_filt)
            
            # Step 4: Window-based analysis
            window_samples = int(duration * self.fs)
            step = int(window_samples * (1 - self.overlap_ratio))
            
            processed_records = []
            start = 0
            
            while start + window_samples <= n_samples:
                window_data = data_clean[start:start + window_samples]
                
                # Compute band powers
                bp_result = self._compute_bandpowers(window_data)
                
                # Compute metrics
                metrics = self._compute_metrics(bp_result['relative'])
                
                # Use timestamp from middle of window
                mid_idx = start + window_samples // 2
                timestamp = (
                    records[mid_idx].timestamp
                    if mid_idx < len(records)
                    else records[-1].timestamp
                )

                
                processed_records.append({
                    'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                    'focus_label': metrics['focus'],  # Named _label to match existing format
                    'stress_label': metrics['stress'],
                    'wellness_label': metrics['mental_readiness'],
                    'engagement': metrics['engagement'],
                    'drowsiness': metrics['drowsiness'],
                    'bandpowers': {k: round(v * 100, 2) for k, v in bp_result['relative'].items()},
                    'dominant_band': bp_result['dominant']
                })
                
                start += step
            
            logger.info(f"Generated {len(processed_records)} processed records")
            return processed_records
            
        except Exception as e:
            logger.error(f"Error in FFT processing: {e}", exc_info=True)
            raise
            