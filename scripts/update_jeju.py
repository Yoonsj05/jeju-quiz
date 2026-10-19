
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# 제주특별자치도 OpenAPI
API_URL = (
    "https://www.jeju.go.kr/rest/"
    "JejuDialectService/getJejuDialectServiceList"
    "?page=1&pageSize=100"
)

OUTPUT_FILE = Path("jeju.xml")

FIELDS = [
    "seq",
    "type",
    "name",
    "siteName",
    "index",
    "contents",
    "engContents",
    "janContents",
    "chiContents",
    "sound",
    "soundUrl",
    "use",
    "category",
]


# XML/HTML 문자 참조 해석
def decode_entities(text):
    for _ in range(5):
        decoded = html.unescape(text)

        if decoded == text:
            break

        text = decoded

    return text


# XML에서 허용하지 않는 제어 문자만 제거
def clean_text(text):
    text = decode_entities(text)

    result = []

    for char in text:
        code = ord(char)

        if (
            code in (9, 10, 13)
            or 0x20 <= code <= 0xD7FF
            or 0xE000 <= code <= 0xFFFD
            or 0x10000 <= code <= 0x10FFFF
        ):
            result.append(char)

    # 제주어 특수 문자는 바꾸지 않음
    return "".join(result)


def get_tag_text(text, tag):
    pattern = (
        r"<" + re.escape(tag) +
        r"(?:\s[^>]*)?>"
        r"(.*?)"
        r"</" + re.escape(tag) + r"\s*>"
    )

    match = re.search(
        pattern,
        text,
        flags=re.DOTALL
    )

    if match is None:
        return ""

    return clean_text(match.group(1).strip())


def download_data():
    print("제주어 OpenAPI 호출 시작")

    request = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/xml, text/xml, */*"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()

    if charset:
        text = raw.decode(
            charset,
            errors="replace"
        )
    else:
        text = raw.decode(
            "utf-8",
            errors="replace"
        )

    print("인터넷에서 API 데이터 수신 완료")
    return text


def create_xml(api_text):
    result_code = get_tag_text(
        api_text,
        "resultCode"
    )

    if result_code != "00":
        raise ValueError(
            "API 응답 오류: " + result_code
        )

    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item\s*>",
        api_text,
        flags=re.DOTALL
    )

    if len(items) < 30:
        raise ValueError(
            "데이터 개수가 너무 적어요: " +
            str(len(items))
        )

    root = ET.Element("jejunetApi")

    ET.SubElement(root, "error").text = "false"
    ET.SubElement(root, "result").text = "SUCCESS"
    ET.SubElement(root, "resultCode").text = "00"

    list_element = ET.SubElement(root, "list")

    for raw_item in items:
        item_element = ET.SubElement(
            list_element,
            "item"
        )

        for field in FIELDS:
            value = get_tag_text(
                raw_item,
                field
            )

            ET.SubElement(
                item_element,
                field
            ).text = value

    query = ET.SubElement(root, "query")

    ET.SubElement(
        query,
        "pageSize"
    ).text = str(len(items))

    ET.SubElement(
        query,
        "page"
    ).text = "1"

    ET.SubElement(
        query,
        "rows"
    ).text = (
        get_tag_text(api_text, "rows")
        or str(len(items))
    )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    tree.write(
        temp_file,
        encoding="utf-8",
        xml_declaration=True
    )

    # 저장된 XML 정상 여부 검사
    ET.parse(temp_file)

    # 검사에 성공한 경우만 갱신
    temp_file.replace(OUTPUT_FILE)

    print("XML 저장 성공")
    print("가져온 단어 수:", len(items))


def main():
    api_text = download_data()
    create_xml(api_text)
    print("OpenAPI 데이터 갱신 완료")


if __name__ == "__main__":
    main()
