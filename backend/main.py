from fastapi import FastAPI

# Initialize the BioGate API
app = FastAPI(title="BioGate API")

@app.get("/health")
def health_check():
    """
    Heartbeat endpoint to verify the server is alive.
    Required for Week 1 Technical Foundation.
    """
    return {
        "status": "healthy", 
        "service": "BioGate", 
        "version": "1.0"
    }
