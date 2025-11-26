from urllib.parse import urlparse, urlunparse


def resolve_docker_url(http_url: str) -> str:
    if not http_url:
        return http_url
    parsed = urlparse(http_url)
    if (
        parsed.hostname
        and "." not in parsed.hostname
        and parsed.hostname != "localhost"
    ):
        new_netloc = parsed.netloc.replace(parsed.hostname, "localhost")
        return urlunparse(parsed._replace(netloc=new_netloc))
    return http_url
