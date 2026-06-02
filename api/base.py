"""Base API class for AI Model integration."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class APIStatus(Enum):
    WAIT = "WAIT"
    RUN = "RUN"
    FAIL = "FAIL"
    DONE = "DONE"


@dataclass
class APIResponse:
    success: bool
    job_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status: Optional[APIStatus] = None


class BaseAPI(ABC):
    def __init__(self, secret_id: str = "", secret_key: str = ""):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self._session = None

    @abstractmethod
    def submit(self, prompt: str = "", image_path: str = "", **kwargs) -> APIResponse:
        """Submit a reconstruction job.
        
        Args:
            prompt: Text description for text-to-3D
            image_path: Path to input image for image-to-3D
            **kwargs: Additional API-specific parameters
            
        Returns:
            APIResponse with job_id for tracking
        """
        pass

    @abstractmethod
    def query(self, job_id: str) -> APIResponse:
        """Query job status and get results.
        
        Args:
            job_id: Job ID from submit()
            
        Returns:
            APIResponse with status and data
        """
        pass

    @abstractmethod
    def download(self, job_id: str, output_path: str) -> APIResponse:
        """Download the result file.
        
        Args:
            job_id: Job ID from submit()
            output_path: Local path to save the result
            
        Returns:
            APIResponse with file path
        """
        pass

    def get_status(self, job_id: str) -> APIStatus:
        """Get job status (convenience method)."""
        response = self.query(job_id)
        if response.success and response.status:
            return response.status
        return APIStatus.FAIL

    def wait_for_completion(self, job_id: str, timeout: int = 600, 
                           poll_interval: int = 5) -> APIResponse:
        """Wait for job to complete.
        
        Args:
            job_id: Job ID from submit()
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between polls
            
        Returns:
            APIResponse when status is FAIL or DONE
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.query(job_id)
            if not response.success:
                return response
            
            if response.status in (APIStatus.FAIL, APIStatus.DONE):
                return response
            
            time.sleep(poll_interval)
        
        return APIResponse(
            success=False,
            error=f"Timeout after {timeout} seconds"
        )

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the API is accessible."""
        pass