
/*
  제주어 학습 웹앱
  데이터 출처: 제주특별자치도 방언사전 OpenAPI
  XML 파일을 읽어 사전 화면에 출력
*/

const XML_FILE = "./jeju.xml";
const PAGE_SIZE = 20;

let words = [];
let currentPage = 1;
let filteredWords = [];

const wordList = document.getElementById("wordList");
const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");
const statusMessage = document.getElementById("statusMessage");
const totalCount = document.getElementById("totalCount");
const pageInfo = document.getElementById("pageInfo");
const prevButton = document.getElementById("prevButton");
const nextButton = document.getElementById("nextButton");

function getXmlText(parent, tagName) {
  const element = parent.querySelector(tagName);
  return element ? element.textContent.trim() : "";
}

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

// XML 데이터를 불러오는 함수
async function loadWords() {
  showStatus("제주어 데이터를 불러오는 중이에요.");

  try {
    const response = await fetch(XML_FILE);

    if (!response.ok) {
      throw new Error("XML 파일 읽기 실패: " + response.status);
    }

    const xmlText = await response.text();

    const parser = new DOMParser();
    const xml = parser.parseFromString(
      xmlText,
      "application/xml"
    );

    if (xml.querySelector("parsererror")) {
      throw new Error("XML 파일 형식이 올바르지 않아요.");
    }

    const resultCode = getXmlText(xml, "resultCode");

    if (resultCode !== "00") {
      throw new Error("API 데이터 응답 코드: " + resultCode);
    }

    const items = Array.from(
      xml.querySelectorAll("list > item")
    );

    words = items.map(function(item) {
      return {
        id: getXmlText(item, "seq"),
        name: getXmlText(item, "name"),
        meaning: getXmlText(item, "contents"),
        soundUrl: getXmlText(item, "soundUrl")
      };
    }).filter(function(word) {
      return word.name && word.meaning;
    });

    if (words.length === 0) {
      throw new Error("XML에서 제주어 단어를 찾지 못했어요.");
    }

    filteredWords = [...words];
    currentPage = 1;

    totalCount.textContent =
      "불러온 단어 " + words.length + "개";

    displayWords();
  } catch (error) {
    console.error("데이터 불러오기 오류:", error);

    totalCount.textContent = "연결 오류";
    wordList.innerHTML = "";

    showStatus(
      "XML 파일을 읽지 못했어요: " + error.message,
      true
    );

    prevButton.disabled = true;
    nextButton.disabled = true;
  }
}

// 현재 페이지의 카드 출력
function displayWords() {
  wordList.innerHTML = "";

  const totalPages = Math.max(
    1,
    Math.ceil(filteredWords.length / PAGE_SIZE)
  );

  const start = (currentPage - 1) * PAGE_SIZE;
  const currentWords = filteredWords.slice(
    start,
    start + PAGE_SIZE
  );

  if (currentWords.length === 0) {
    showStatus("검색 결과가 없어요.");
  } else {
    showStatus("");
  }

  currentWords.forEach(function(word) {
    const card = document.createElement("div");
    card.className = "word-card";

    const title = document.createElement("h3");
    title.textContent = word.name;

    const meaning = document.createElement("p");
    meaning.textContent = word.meaning;

    card.appendChild(title);
    card.appendChild(meaning);

    // 발음이 제공되는 단어에만 버튼 표시
    if (word.soundUrl) {
      const button = document.createElement("button");
      button.className = "sound-button";
      button.textContent = "발음 듣기";

      button.addEventListener("click", function() {
        const audio = new Audio(word.soundUrl);

        audio.play().catch(function() {
          alert("이 단어의 음성을 재생할 수 없어요.");
        });
      });

      card.appendChild(button);
    }

    wordList.appendChild(card);
  });

  pageInfo.textContent =
    currentPage + " / " + totalPages + "페이지";

  prevButton.disabled = currentPage <= 1;
  nextButton.disabled = currentPage >= totalPages;
}

// 제주어 또는 뜻 검색
function searchWords() {
  const keyword = searchInput.value.trim().toLowerCase();

  filteredWords = words.filter(function(word) {
    return (
      word.name.toLowerCase().includes(keyword) ||
      word.meaning.toLowerCase().includes(keyword)
    );
  });

  currentPage = 1;
  displayWords();
}

// 검색 버튼
searchButton.addEventListener("click", searchWords);

// 엔터키 검색
searchInput.addEventListener("keydown", function(event) {
  if (event.key === "Enter") {
    searchWords();
  }
});

// 입력 내용 삭제 시 목록 복원
searchInput.addEventListener("input", function() {
  if (searchInput.value.trim() === "") {
    filteredWords = [...words];
    currentPage = 1;
    displayWords();
  }
});

// 이전 페이지
prevButton.addEventListener("click", function() {
  if (currentPage > 1) {
    currentPage--;
    displayWords();
  }
});

// 다음 페이지
nextButton.addEventListener("click", function() {
  const totalPages = Math.ceil(
    filteredWords.length / PAGE_SIZE
  );

  if (currentPage < totalPages) {
    currentPage++;
    displayWords();
  }
});

// 페이지 실행
loadWords();
