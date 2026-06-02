"""Tencent Hunyuan3D API implementation using official SDK."""

import os
import time
import base64
from tencentcloud.ai3d.v20250513 import ai3d_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile import client_profile

from .base import BaseAPI, APIResponse, APIStatus


class Hunyuan3DAPI(BaseAPI):
    """Hunyuan3D API using Tencent Cloud SDK."""

    def __init__(self, secret_id: str = "", secret_key: str = ""):
        super().__init__(secret_id, secret_key)
        self._client = None

    def _get_client(self):
        """Get or create Tencent Cloud AI3D client."""
        if self._client is not None:
            return self._client

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = client_profile.HttpProfile()
        http_profile.endpoint = "ai3d.tencentcloudapi.com"
        client_profile_obj = client_profile.ClientProfile()
        client_profile_obj.httpProfile = http_profile
        self._client = ai3d_client.Ai3dClient(cred, "ap-guangzhou", client_profile_obj)
        return self._client

    def submit(self, prompt: str = "", image_path: str = "", **kwargs) -> APIResponse:
        """Submit a Hunyuan3D reconstruction job."""
        if not self.secret_id or not self.secret_key:
            return APIResponse(success=False, error="Secret ID and Secret Key are required")

        try:
            client = self._get_client()
            req = models.SubmitHunyuanTo3DProJobRequest()

            if image_path:
                if not os.path.exists(image_path):
                    return APIResponse(success=False, error=f"Image file not found: {image_path}")

                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                req.ImageBase64 = image_data
            elif prompt:
                req.Prompt = prompt
            else:
                return APIResponse(success=False, error="Either prompt or image_path is required")

            if prompt and image_path:
                req.Prompt = prompt

            if kwargs.get("face_count"):
                req.FaceCount = kwargs.get("face_count")

            req.ResultFormat = "GLB"
            req.Model = "3.1"
            req.GenerateType = "Normal"
            print(f"DEBUG: SubmitHunyuanTo3DProJob - ResultFormat: {req.ResultFormat}, Model: {req.Model}, GenerateType: {req.GenerateType}")

            resp = client.SubmitHunyuanTo3DProJob(req)

            if not resp.JobId:
                return APIResponse(success=False, error="No JobId returned")

            return APIResponse(success=True, job_id=resp.JobId, status=APIStatus.WAIT)

        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def query(self, job_id: str) -> APIResponse:
        """Query Hunyuan3D job status."""
        if not self.secret_id or not self.secret_key:
            return APIResponse(success=False, error="Secret ID and Secret Key are required")

        try:
            client = self._get_client()
            req = models.QueryHunyuanTo3DProJobRequest()
            req.JobId = job_id

            resp = client.QueryHunyuanTo3DProJob(req)

            status_map = {
                "WAIT": APIStatus.WAIT,
                "RUN": APIStatus.RUN,
                "FAIL": APIStatus.FAIL,
                "DONE": APIStatus.DONE,
            }
            status = status_map.get(resp.Status, APIStatus.WAIT)

            return APIResponse(
                success=True,
                job_id=job_id,
                status=status,
                data={
                    "Status": resp.Status,
                    "ResultFile3Ds": getattr(resp, "ResultFile3Ds", []),
                }
            )

        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def download(self, job_id: str, output_path: str) -> APIResponse:
        """Download the result GLB file."""
        import requests

        response = self.query(job_id)
        if not response.success:
            return response

        if response.status != APIStatus.DONE:
            return APIResponse(
                success=False,
                error=f"Job not done, status: {response.status}"
            )

        result_files = response.data.get("ResultFile3Ds", [])
        if not result_files:
            return APIResponse(success=False, error="No result files returned")

        print(f"DEBUG: result_files type: {type(result_files)}, content: {result_files}")
        
        file_url = result_files[0].Url if hasattr(result_files[0], 'Url') else result_files[0].get('Url')
        if not file_url:
            return APIResponse(success=False, error="No file URL in result")
        
        print(f"DEBUG: file_url = {file_url}")

        try:
            resp = requests.get(file_url, timeout=300)
            resp.raise_for_status()

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)

            return APIResponse(success=True, data={"file_path": output_path})

        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 5) -> APIResponse:
        """Wait for job completion."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.query(job_id)
            if not result.success:
                return result
            if result.status == APIStatus.DONE:
                return result
            if result.status == APIStatus.FAIL:
                return result
            time.sleep(poll_interval)
        return APIResponse(success=False, error="Timeout waiting for job completion")

    def test_connection(self) -> bool:
        """Test if the API is accessible."""
        if not self.secret_id or not self.secret_key:
            return False
        try:
            client = self._get_client()
            req = models.QueryHunyuanTo3DProJobRequest()
            req.JobId = "test"
            client.QueryHunyuanTo3DProJob(req)
            return True
        except:
            return False