import argparse
import http.client
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REQUESTS_COUNT = 10
CHUNK_SIZE = 64 * 1024
TIMEOUT = 60


class IncompleteResponse(Exception):
    pass


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "speedtest/1.0", "Cache-Control": "no-cache"})
    size = 0
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        expected = response.headers.get("Content-Length")
        encoded = response.headers.get("Content-Encoding", "identity").lower() != "identity"
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
    elapsed = time.perf_counter() - start
    if expected is not None and expected.isdigit() and not encoded and size != int(expected):
        raise IncompleteResponse(f"получено {size} байт из {expected}, соединение оборвалось")
    return size, elapsed


def main():
    parser = argparse.ArgumentParser(description="Измерение скорости скачивания по URL")
    parser.add_argument("url", help="адрес ресурса, например http://example.com/big.jpg")
    parser.add_argument("-n", "--count", type=int, default=REQUESTS_COUNT, help="количество запросов (по умолчанию 10)")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("количество запросов должно быть положительным")
    if urllib.parse.urlparse(args.url).scheme.lower() not in ("http", "https"):
        parser.error("адрес должен начинаться с http:// или https://")

    total_bytes = 0
    total_time = 0.0

    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(args.url)
        except (urllib.error.URLError, http.client.HTTPException, IncompleteResponse, OSError, ValueError) as error:
            print(f"Запрос {i}: ошибка — {str(error).strip() or type(error).__name__}", file=sys.stderr)
            return 1
        total_bytes += size
        total_time += elapsed
        print(f"Запрос {i:>2}: {size / 1_000_000:.2f} MB за {elapsed:.3f} с")

    average_time = total_time / args.count
    speed_mbit = total_bytes * 8 / total_time / 1_000_000 if total_time > 0 else 0.0

    print()
    print(f"Среднее время запроса: {average_time:.3f} с")
    print(f"Всего скачано: {total_bytes / 1_000_000:.2f} MB ({total_bytes} байт)")
    print(f"Скорость скачивания: {speed_mbit:.2f} Мбит/с")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
