from .awswaf.aws import AwsWaf
from curl_cffi.requests import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from loguru import logger


class AwsWafTokenError(Exception):
    """Custom exception for AWS WAF token failures"""
    pass


class AsyncAwsWafSolver:
    def __init__(self, session: AsyncSession):
        self.session = session

        self._log = logger.bind(component="binance_cookies")

    async def _is_token_valid(self, url: str) -> bool:
        """Check if token is valid (not empty and proper length)"""
        verification_response = await self.session.get(url)
        resp_text = verification_response.text

        return (len(resp_text) > 20000 and
                "In order to continue, we need to verify that you're not a robot" not in resp_text)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=lambda x: print(f"№{x.attempt_number} Retrying. {x.outcome.exception()}"),
        # retry=retry_if_exception_type(AwsWafTokenError),
        reraise=True
    )
    async def solve(self, url: str) -> str:
        """Solve AWS WAF challenge for a given URL with retry logic"""
        # Initial request to get challenge
        response = await self.session.get(url)
        print(1, response.status_code)
        print(response.text)

        goku, host = AwsWaf.extract(response.text)

        if not goku or not host:
            raise AwsWafTokenError("Failed to extract challenge data from response")

        # Solve the challenge
        token = AwsWaf(goku, host, url.split('/')[2])()

        # Verify token works
        self.session.headers.update({"cookie": f"aws-waf-token={token}"})

        if not await self._is_token_valid(url):
            self._log.debug(f"Token verification failed")
            raise AwsWafTokenError("Token verification failed")

        self._log.debug("Token verified successfully")

        return token
