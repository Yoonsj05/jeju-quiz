
# ==========================================
# 제주어 OpenAPI 자동 데이터 갱신
# 공공데이터포털 등록 API
# 제공기관: 제주특별자치도
# ==========================================

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# 실제 제주어 OpenAPI 주소
API_URL = (
    "https://www.jeju.go.kr/rest/"
    "JejuDialectService/getJejuDialectServiceList"
    "?page=1&pageSize=100"
)

# 저장할 XML 파일
OUTPUT_FILE = Path("jeju.xml")

# 가져올 데이터 항목
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


# XML 태그 안의 내용 추출
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

    return html.unescape(match.group(1).strip())


# 표시하기 어려운 특수 문자 정리
def clean_text(text):
    result = []

    for char in text:
        code = ord(char)

        # 원본에서 네모로 보이던 사설 영역 문자
        if 0xE000 <= code <= 0xF8FF:
            result.append("~")
        else:
            result.append(char)

    return "".join(result)


# OpenAPI 데이터 요청
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
        text = raw.decode(charset, errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace")

    print("API 응답 수신 완료")

    return text


# 제주어 데이터 정리 및 XML 생성
def create_xml(api_text):

    result_code = get_tag_text(
        api_text,
        "resultCode"
    )

    if result_code != "00":
        raise ValueError(
            "API 응답 실패: " + result_code
        )

    # API에서 반환한 item 추출
    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item\s*>",
        api_text,
        flags=re.DOTALL
    )

    if len(items) < 30:
        raise ValueError(
            "API 단어 수가 비정상적이에요: " +
            str(len(items))
        )

    root = ET.Element("jejunetApi")

    ET.SubElement(root, "error").text = "false"
    ET.SubElement(root, "result").text = "SUCCESS"
    ET.SubElement(root, "resultCode").text = "00"
    ET.SubElement(root, "resultMsg").text = "success"

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

            value = clean_text(value)

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
    ).text = get_tag_text(
        api_text,
        "rows"
    ) or str(len(items))

    tree = ET.ElementTree(root)

    ET.indent(
        tree,
        space="  ",
        level=0
    )

    # 임시 파일에 먼저 저장
    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    tree.write(
        temp_file,
        encoding="utf-8",
        xml_declaration=True
    )

    # XML 문법 검사
    ET.parse(temp_file)

    # 검증에 성공한 경우에만 기존 파일 교체
    temp_file.replace(OUTPUT_FILE)

    print(
        "XML 저장 성공:",
        len(items),
        "개 단어"
    )


# 실행 시작
def main():
    api_text = download_data()
    create_xml(api_text)

    print("제주어 데이터 갱신 완료")


if __name__ == "__main__":
    main()
