# Text Retrieval System (한국어 텍스트 검색 시스템)

이 프로젝트는 BM25F 알고리즘을 기반으로 한 한국어 텍스트 검색 시스템입니다. JSON 형식의 특허 데이터(Title, Abstract, Claims)를 색인하고, 다양한 쿼리 옵션을 통해 정밀한 검색 기능을 제공합니다.

## ✨ 주요 기능

### 1. 색인 (Indexing)
- 주어진 데이터 디렉토리 내의 JSON 파일들을 읽어 역색인(Inverted Index) 구조를 생성합니다.
- `src/indexer.py`는 문서별/필드별 단어 빈도(TF)를 분석하여 `term_dict.json`(단어 사전), `postings.bin`(포스팅 리스트), `doc_table.json`(문서 정보)을 생성합니다.
- **다중 필드 지원**: `Title`(발명의 명칭), `Abstract`(요약), `Claims`(청구항) 3가지 필드를 구분하여 색인합니다.

### 2. 검색 (Searching)
- **BM25F 랭킹 알고리즘**: 문서의 길이와 필드별 가중치(`Title` > `Abstract` > `Claims`)를 고려하여 검색어와의 연관성을 점수화(Scoring)합니다.
- **고급 검색 쿼리 지원**:
    - `[AND]`: 모든 검색어가 포함된 문서만 검색 (예: `[AND] 데이터 보안`)
    - `[PHRASE]`: 정확히 일치하는 구문 검색 (Title 필드 대상, 예: `[PHRASE] 인공지능 시스템`)
    - `[FIELD=T/A/C]`: 특정 필드 한정 검색 (Title, Abstract, Claims, 예: `[FIELD=T] 반도체`)
    - `[VERBOSE]`: 검색 결과에서 매칭된 스니펫(Snippet)을 하이라이팅하여 출력 (예: `[VERBOSE] 딥러닝`)

### 3. 하이라이팅 (Highlighting)
- `[VERBOSE]` 옵션 사용 시, 검색어가 포함된 문맥을 추출하여 `<<검색어>>` 형태로 강조하여 보여줍니다.
- 대소문자를 구분하지 않고 정확하게 매칭되는 부분을 찾아 보여줍니다.

## 🛠️ 기술 스택

- **Language**: Python 3
- **Morphological Analysis**: `KoNLPy` (Komoran) - 한국어 형태소 분석 및 명사 추출
- **Algorithm**: BM25F (Probabilistic Information Retrieval)

## 📂 프로젝트 구조

```bash
.
├── main.py             # 프로그램 실행 진입점 (CLI)
├── src/
│   ├── indexer.py      # 색인 생성 로직 (Inverted Index Build)
│   ├── searcher.py     # 검색 로직 (BM25F Scoring, Query Parsing)
│   └── tokenizer.py    # 형태소 분석기 래퍼 (Komoran)
├── index/              # 생성된 인덱스 파일 저장소 (자동 생성)
└── REQUEST.md          # 사용자 요구사항 정의
```

## 사용 방법

### 1. 환경 설정
필요한 라이브러리를 설치합니다.
```bash
pip install -r requirements.txt
# 또는
pip install konlpy
```

### 2. 실행
`main.py`를 실행하여 색인 또는 검색 작업을 수행할 수 있습니다.
```bash
python main.py
```

### 3. 색인 (Indexing)
프로그램 실행 후 `index` (또는 `i`)를 입력하면 `data/` 경로의 파일들을 읽어 색인을 생성합니다.
```text
작업을 선택하세요 (index/search): index
...
색인이 완료되었습니다.
```

### 4. 검색 (Searching)
프로그램 실행 후 `search` (또는 `s`)를 입력하면 검색 모드로 진입합니다.

**기본 검색 (OR 검색)**
```text
검색어를 입력하세요: 인공지능 데이터
```

**AND 검색**
```text
검색어를 입력하세요: [AND] 스마트 홈
```

**구문 검색 (Phrase Search)**
```text
검색어를 입력하세요: [PHRASE] 자율 주행
```

**필드 지정 검색**
- `[FIELD=T]`: 제목(Title) 검색
- `[FIELD=A]`: 요약(Abstract) 검색
- `[FIELD=C]`: 청구항(Claims) 검색
```text
검색어를 입력하세요: [FIELD=T] 디스플레이
```

**상세 보기 (Verbose)**
- 검색 결과의 스니펫을 함께 보고 싶을 때 사용
```text
검색어를 입력하세요: [AND][VERBOSE] 네트워크 보안
```

## 인덱스 파일 정보
- **term_dict.json**: 단어별 문서 빈도(DF) 및 포스팅 파일 내 위치 정보
- **doc_table.json**: 문서 ID 매핑 및 필드별 길이 정보
- **postings.bin**: 단어별 출현 문서 ID 및 필드별 빈도(TF)를 저장한 이진 파일
