from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.models.resume import ResumeAnalysisResponse
from backend.services.resume_service import extract_text_from_pdf_bytes, analyze_resume_text

router = APIRouter(prefix="/resume", tags=["Resume & ATS Analyzer"])


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume and receive ATS compatibility score and feedback.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume files are currently supported."
        )

    try:
        content = await file.read()
        extracted_text = extract_text_from_pdf_bytes(content)
        if not extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract readable text from this PDF. Please ensure it is not a scanned image."
            )

        analysis, err = analyze_resume_text(extracted_text)
        if err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=err
            )

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
