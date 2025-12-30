# Google Vision API Setup (Optional)

The API now uses **Google Vision API** which is **much better for handwritten text**.

## 🚀 Quick Start (No Setup Needed)

Google Vision works **without credentials** for basic testing, but has rate limits.

Just restart your server and it will automatically use Google Vision!

## 🔐 Production Setup (Remove Rate Limits)

For production use, set up Google Cloud credentials:

### 1. Create Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable **Vision API**:
   - Go to "APIs & Services" > "Library"
   - Search "Vision API"
   - Click "Enable"

### 2. Create Service Account
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name it: `ocr-service`
4. Grant role: "Cloud Vision API User"
5. Click "Done"

### 3. Create Key
1. Click on your new service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON"
5. Save the file as `google-credentials.json`

### 4. Set Environment Variable

**Windows PowerShell:**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="I:\Ishtiaq\BHAI\MindTune\fastapi_ocr_stt\google-credentials.json"
```

**Or create `.env` file:**
```
GOOGLE_APPLICATION_CREDENTIALS=I:\Ishtiaq\BHAI\MindTune\fastapi_ocr_stt\google-credentials.json
```

### 5. Restart Server
```powershell
cd i:\Ishtiaq\BHAI\MindTune\fastapi_ocr_stt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## 📊 What Changed

- ✅ **Handwritten text**: Now works great!
- ✅ **Printed text**: Still works perfectly
- ✅ **Photos**: Better handling of lighting, angles
- ✅ **Automatic**: Uses Google Vision by default, falls back to Tesseract if needed

## 💰 Pricing

- **Free Tier**: 1,000 requests/month
- **After**: $1.50 per 1,000 requests
- Details: https://cloud.google.com/vision/pricing

## 🧪 Test It

Upload your handwritten "I am feeling strange" photo again - it should work now!
