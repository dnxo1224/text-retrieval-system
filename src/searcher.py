# src/searcher.py
import os
import struct
import math
import json
from .tokenizer import extract_terms
class Searcher:
    def __init__(self, index_dir, doc_table_file, term_dict_file, postings_file):
    # load index_dir/...
        self.index_dir = os.path.abspath(index_dir) 
        postings_file = os.path.join(self.index_dir, postings_file)
        term_dict_file = os.path.join(self.index_dir, term_dict_file)
        doc_table_file = os.path.join(self.index_dir, doc_table_file)

    # load doc_table → self.doc_table
    # load term_dict → self.term_dcit
    # open posting file → self.fp
        with open(doc_table_file, 'r', encoding='utf-8') as f:
            self.doc_table = json.load(f)
        with open(term_dict_file, 'r', encoding='utf-8') as f:
            self.term_dict = json.load(f)
        self.fp = open(postings_file, 'rb')
    # 총문서 크기 → self.N
        self.N = len(self.doc_table)

    def close(self): # __init__에서 안 닫아줘서 클래스가 닫힐 때 닫기
        if self.fp:
            self.fp.close()
            

    def get_postings(self, term):
        if term not in self.term_dict:
            return []
        # term == 'ai'  
        entry = self.term_dict[term]
        df = entry["df"] # 123
        start_offset = entry["start"] # 0
        postings = []

        self.fp.seek(start_offset) # posting_file 에서 0번 byte offset으로 커서를 이동
        
        for _ in range(df): # df(range) 만큼 반복
            data = self.fp.read(8) 
            # 커서 이동 후에 start 지점에서 8바이트 읽기 (8바이트 안에 몇번째 파일(4byte)에 해당 term이 몇 번(4byte) 나왔는지에 대한 정보가 담겨있음.)
            if len(data) != 8:
                raise ValueError(f"Incomplete data read at offset {start_offset}") # 8바이트 정보가 아니면 오프셋 에러 출력.
            doc_id, freq = struct.unpack("ii", data) # 바이트 -> int로 변환
            postings.append((doc_id, freq)) # postings 안에 doc_id랑 freq를 집어넣기.
        return postings
    
    
    def process_query(self, user_query): # ex) process_query(데이터와 보안)
    # query term 전처리
        query_terms = extract_terms(user_query) # [데이터, 보안]
        
    # search main
        doc_scores = {} # 랭크 값 {[0, 15], [5, 12], ... }
        for term in query_terms:
            if term not in self.term_dict:
                continue
            df = self.term_dict[term]["df"] # 데이터 의 df를 df에 저장
            idf = math.log((self.N + 1) / (df + 1)) + 1 # N: 총 문서 수 
            postings = self.get_postings(term)
            for doc_id, tf in postings:
                tf_idf = tf * idf
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + tf_idf
                # 랭킹 값이 doc_scores로 들어감. 
                # ex) {doc_id:tf_idf} 101:0.5 가 들어오고 101:0.8이 또 들어오면 101:1.3이 되는 원리. term들이 겹칠수록 점수가 높아진다.
        # doc_scores의 상위 5개 문서를 추출해서 새로운 리스트로 만들자.
        sorted_doc_scores = sorted(doc_scores.items(), key = lambda x:x[1], reverse=True) # if_idf 높은순으로 정렬
        top5_doc_scores = sorted_doc_scores[:5] # 5개만 따로 리스트 만들기
        
        print(f'''RESULT:
        검색어: {query_terms}
        총 {len(doc_scores)}개 문서 검색
        상위 5개 문서:
        ''')
        for idx, score in top5_doc_scores:
            print(f'{self.doc_table[idx]["filename"]} {round(score,2)}')