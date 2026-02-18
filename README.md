# Bank Statement Analyzer (BSA)

Secure internal tool for visa application financial analysis.

## Features
- **Secure JWT Auth**: Private access only.
- **Multiformat Extraction**: Support for PDF, CSV, and Excel.
- **Financial Analysis**: Automatic calculation of monthly summaries and averages.
- **AI Classification**: Uses OpenAI to categorize unusual deposits (≥ 50k ₦).
- **Modern Dashboard**: Built with React and Tailwind CSS.

## Quick Start (Root Directory)
1. **Initialize Backend**: `pip install -r backend/requirements.txt`
2. **Initialize Frontend**: `cd frontend && npm install`
3. **Run App**:
   - Start Frontend: `npm run dev` (or `npm run frontend`)
   - Start Backend: `npm run backend`

### Manual Commands
- **Backend**: `python -m backend.main`
- **Frontend**: `cd frontend && npm run dev`


## Production Deployment
- Deployed at: http://BSA.NoAgentTravelGuide.com
- Environment: Hostinger, HTTPS required.
- Set all environment variables on the host.

## Tech Stack
- **Backend**: FastAPI, Pandas, pdfplumber, OpenAI GPT.
- **Frontend**: React, Tailwind CSS, Lucide Icons.
