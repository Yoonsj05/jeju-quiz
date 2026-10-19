
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# 제주특별자치도 방언사전 OpenAPI
API_URL = (
    "https://www.jeju.go.kr/rest/"
    "JejuDialectService/getJejuDialectServiceList"
    "?page=1&pageSize=100"
)

# 한양 PUA -> 표준 유니코드 옛한글 변환표
MAPPING_URL = (
    "https://raw.githubusercontent.com/"
    "mete0r/hypua2jamo/master/data/"
    "hypua2jamocomposed.txt"
)

OUTPUT_FILE = Path("jeju.xml")

FIELDS = [
    "seq", "type", "name", "siteName", "index",
    "contents", "engContents", "janContents",
    "chiContents", "sound", "soundUrl",
    "use", "category"
]


# 인터넷에서 자료 가져오기
def download_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request, timeout=40
    ) as response:
        raw = response.read()
        charset = (
            response.headers.get_content_charset()
            or "utf-8"
        )

    return raw.decode(charset)


# 옛한글 변환표 불러오기
def load_mapping():
    print("옛한글 변환표 다운로드 시작")

    text = download_text(MAPPING_URL)
    mapping = {}

    for line in text.splitlines():
        line = line.strip()

        if not line.startswith("U+"):
            continue

        if "=>" not in line:
            continue

        left, right = line.split("=>", 1)

        source = int(
            left.strip().replace("U+", ""),
            16
        )

        targets = re.findall(
            r"U\+([0-9A-Fa-f]+)",
            right
        )

        if not targets:
            continue

        converted = "".join(
            chr(int(code, 16))
            for code in targets
        )

        mapping[source] = converted

    if len(mapping) < 5000:
        raise ValueError(
            "옛한글 변환표가 불완전합니다."
        )

    # 사용자가 보여준 문자 검증
    expected = "\u110e\u119e"

    if mapping.get(0xF341) != expected:
        raise ValueError(
            "옛한글 변환표 검증 실패"
        )

    print(
        "옛한글 변환표 로딩 성공:",
        len(mapping), "개"
    )

    return mapping


# XML 문자 참조 해석
def decode_entities(text):
    for _ in range(5):
        decoded = html.unescape(text)

        if decoded == text:
            break

        text = decoded

    return text


# 원본 제주어 특수 문자를 표준 옛한글로 변환
def convert_old_hangul(text, mapping):
    text = decode_entities(text)

    result = []

    for char in text:
        code = ord(char)

        if code in mapping:
            result.append(mapping[code])
        else:
            # 매핑이 없는 문자는 원본 보존
            result.append(char)

    converted = "".join(result)

    # XML에서 허용하지 않는 제어 문자만 제거
    converted = "".join(
        char for char in converted
        if (
            ord(char) in (9, 10, 13)
            or 0x20 <= ord(char) <= 0xD7FF
            or 0xE000 <= ord(char) <= 0xFFFD
            or 0x10000 <= ord(char) <= 0x10FFFF
        )
    )

    return converted


# XML 태그의 내용 읽기
def get_tag_text(text, tag, mapping):
    pattern = (
        r"<" + re.escape(tag) +
        r"(?:\s[^>]*)?>"
        r"(.*?)"
        r"</" + re.escape(tag) + r"\s*>"
    )

    match = re.search(
        pattern, text, flags=re.DOTALL
    )

    if match is None:
        return ""

    return convert_old_hangul(
        match.group(1).strip(),
        mapping
    )


# XML 생성
def create_xml(api_text, mapping):
    result_code = get_tag_text(
        api_text, "resultCode", mapping
    )

    if result_code != "00":
        raise ValueError(
            "제주어 API 응답 오류: " + result_code
        )

    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item\s*>",
        api_text,
        flags=re.DOTALL
    )

    if len(items) < 30:
        raise ValueError(
            "제주어 항목이 너무 적습니다: " +
            str(len(items))
        )

    root = ET.Element("jejunetApi")

    ET.SubElement(root, "error").text = "false"
    ET.SubElement(root, "result").text = "SUCCESS"
    ET.SubElement(root, "resultCode").text = "00"

    list_element = ET.SubElement(root, "list")

    for raw_item in items:
        item_element = ET.SubElement(
            list_element, "item"
        )

        for field in FIELDS:
            value = get_tag_text(
                raw_item, field, mapping
            )

            ET.SubElement(
                item_element, field
            ).text = value

    query = ET.SubElement(root, "query")

    ET.SubElement(
        query, "pageSize"
    ).text = str(len(items))

    ET.SubElement(
        query, "page"
    ).text = "1"

    ET.SubElement(
        query, "rows"
    ).text = (
        get_tag_text(api_text, "rows", mapping)
        or str(len(items))
    )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    # 안전하게 임시 파일에 먼저 저장
    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    tree.write(
        temp_file,
        encoding="utf-8",
        xml_declaration=True
    )

    # XML 문법 검사
    ET.parse(temp_file)

    # 검사에 성공했을 때만 실제 파일 교체
    temp_file.replace(OUTPUT_FILE)

    print("제주어 단어 수:", len(items))
    print("옛한글 변환 및 XML 저장 완료")


def main():
    print("제주어 OpenAPI 자동 갱신 시작")

    mapping = load_mapping()
    api_text = download_text(API_URL)

    create_xml(api_text, mapping)

    print("모든 작업 완료")


if __name__ == "__main__":
    main()
