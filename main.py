# main.py
from src.indexer import Indexer
from src.searcher import Searcher

# 설정
DATA_DIR = r"/Users/seolwootae/indexer-dnxo1224/data" # data path
INDEX_DIR = "index" # indexer 출력 dir / indexer.py의 출력 결과 파일 dir.
DOC_TABLE_FILE = "doc_table.json"
TERM_DICT_FILE = "term_dict.json"
POSTINGS_FILE = "postings.bin"

if __name__ == "__main__":

    task = input("작업을 선택하세요 (index/search): ").strip().lower() # 입력값이 잘못들어가도 인지할 수 있도록 strip,lower 사용.

    if task in ("index", "i"): # input 입력 받은 값이 index or i 가 들어가면 실행. 오타가 있어도 실행되는게 진짜 좋은 것 같음 !! 
        indexer = Indexer(DATA_DIR, INDEX_DIR, DOC_TABLE_FILE, TERM_DICT_FILE, POSTINGS_FILE) 
        # 설정값을 그대로 불러오게 만들었음. 유지보수를 위한 클래스화
        indexer.build_index() # indexer 패키지의 인덱스 빌드 코드를 실행.
        print(f"색인이 완료되었습니다. 색인 결과는 '{INDEX_DIR}'에 저장되었습니다.")

    elif task in ("search","s"):
        searcher = Searcher(INDEX_DIR, DOC_TABLE_FILE, TERM_DICT_FILE, POSTINGS_FILE)

        while True:
            input_query = input("검색어를 입력하세요.: ").strip()
            if not input_query:
                break
            searcher.process_query(input_query)