#!/usr/bin/env python3
"""
swagger_fetcher.py - Fetch OpenAPI/Swagger JSON from a Swagger UI URL
Supports OpenAPI 2.0 and 3.0
"""

import json
import sys
import re
import requests
from urllib.parse import urlparse, urljoin
import argparse
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SwaggerFetcher:
    """Fetch OpenAPI/Swagger JSON from a Swagger UI URL"""

    # Common paths where the JSON file might be hosted
    COMMON_PATHS = [
        '/v3/api-docs',
        '/v2/api-docs',
        '/swagger.json',
        '/swagger/v1/swagger.json',
        '/api-docs',
        '/openapi.json',
        '/spec.json',
        '/api/swagger.json',
        '/docs/swagger.json',
        '/swagger-ui/swagger.json',
    ]

    def __init__(self, base_url: str, timeout: int = 10):
        """
        Args:
            base_url: The Swagger UI URL (e.g., https://example.com/swagger-ui/index.html)
            timeout: Request timeout in seconds
        """
        self.base_url = self._normalize_url(base_url)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SwaggerFetcher/1.0 (Python)',
            'Accept': 'application/json, */*'
        })

    def _normalize_url(self, url: str) -> str:
        """Normalize URL: remove /swagger-ui/index.html and keep the base domain"""
        parsed = urlparse(url)
        path = parsed.path
        # Remove /swagger-ui/... if present
        if '/swagger-ui' in path:
            path = path[:path.index('/swagger-ui')]
        if not path or path == '/':
            path = ''
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _try_path(self, path: str) -> tuple[bool, dict | None]:
        """Attempt to fetch JSON from a given path"""
        url = urljoin(self.base_url, path)
        try:
            logger.info(f"Trying: {url}")
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if self._is_valid_swagger(data):
                        logger.info(f"✅ Found file at: {url}")
                        return True, data
                    else:
                        logger.debug(f"File at {url} is not a valid Swagger file")
                except json.JSONDecodeError:
                    logger.debug(f"Response from {url} is not valid JSON")
            else:
                logger.debug(f"Failed: {url} - status {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error for {url}: {e}")
        return False, None

    def _is_valid_swagger(self, data: dict) -> bool:
        """Check if the data is a valid Swagger/OpenAPI file"""
        if 'swagger' in data or 'openapi' in data:
            return True
        if 'paths' in data and 'info' in data:
            return True
        return False

    def fetch(self) -> dict | None:
        """Try to fetch the JSON file from all possible paths"""
        logger.info(f"🔍 Searching for Swagger/OpenAPI file at: {self.base_url}")

        # 1. Try common paths
        for path in self.COMMON_PATHS:
            found, data = self._try_path(path)
            if found:
                return data

        # 2. Try to infer the path from the Swagger UI page itself
        logger.info("Attempting to infer path from Swagger UI page...")
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            if response.status_code == 200:
                html = response.text
                patterns = [
                    r'url\s*:\s*["\']([^"\']+\.json)["\']',
                    r'url\s*=\s*["\']([^"\']+\.json)["\']',
                    r'configuration\.url\s*=\s*["\']([^"\']+\.json)["\']',
                    r'"url"\s*:\s*"([^"]+\.json)"',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    for match in matches:
                        if not match.startswith('http'):
                            match = urljoin(self.base_url, match)
                        found, data = self._try_path(match)
                        if found:
                            return data
        except Exception as e:
            logger.debug(f"Error parsing Swagger UI page: {e}")

        logger.error("❌ Could not find Swagger/OpenAPI JSON file")
        return None

    def save(self, data: dict, output_file: str = 'swagger.json'):
        """Save the data to a JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ File saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch OpenAPI/Swagger JSON from a Swagger UI URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python swagger_fetcher.py https://cleaningapi.twintech-it.com/swagger-ui/index.html
  python swagger_fetcher.py https://example.com/swagger-ui/index.html -o my_api.json
  python swagger_fetcher.py https://example.com/swagger-ui/index.html -v
        """
    )
    parser.add_argument('url', help='Swagger UI URL (e.g., https://example.com/swagger-ui/index.html)')
    parser.add_argument('-o', '--output', default='swagger.json', help='Output file name (default: swagger.json)')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed logs')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    fetcher = SwaggerFetcher(args.url, timeout=args.timeout)
    data = fetcher.fetch()

    if data:
        fetcher.save(data, args.output)
        print(f"\n🎉 File fetched successfully! You can now use it with swagger_to_ai.py:")
        print(f"   python swagger_to_ai.py {args.output}")
        sys.exit(0)
    else:
        print("\n❌ Failed to fetch file. Please check:")
        print("   - The URL is correct")
        print("   - Your internet connection")
        print("   - The server is reachable")
        print("\n💡 You can try:")
        print("   - Use -v for more details")
        print("   - Provide the direct JSON URL if you know it")
        sys.exit(1)


if __name__ == "__main__":
    main()