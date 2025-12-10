# src/searcher.py
import os
import struct
import math
import json
import re
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
            data = self.fp.read(16) 
            # 커서 이동 후에 start 지점에서 16바이트 읽기 (8바이트 안에 몇번째 파일(4byte)에 해당 term이 몇 번(4byte) 나왔는지에 대한 정보가 담겨있음.)
            if len(data) != 16:
                raise ValueError(f"Incomplete data read at offset {start_offset}") # 8바이트 정보가 아니면 오프셋 에러 출력.
            doc_id, tf_title, tf_abstract, tf_claims = struct.unpack("iiii", data) # 바이트 -> int로 변환
            postings.append((doc_id, tf_title, tf_abstract, tf_claims)) # postings 안에 doc_id랑 freq를 집어넣기.
        return postings
    
    
    def process_query(self, user_query): # ex) process_query(데이터와 보안)
        # 1. 태그 파싱 ([AND], [FIELD=...], [PHRASE])
        is_phrase_query = "[PHRASE]" in user_query
        is_and_query = "[AND]" in user_query or is_phrase_query # Phrase Query는 암묵적으로 AND 조건을 포함
        
        target_fields = []
        if "[FIELD=T]" in user_query or is_phrase_query: target_fields.append("title") # Phrase는 Title만 검색
        if "[FIELD=A]" in user_query and not is_phrase_query: target_fields.append("abstract")
        if "[FIELD=C]" in user_query and not is_phrase_query: target_fields.append("claims")
        
        # 태그 제거 후 검색어 추출
        clean_query = user_query.replace("[AND]", "").replace("[FIELD=T]", "").replace("[FIELD=A]", "").replace("[FIELD=C]", "").replace("[PHRASE]", "").replace("[VERBOSE]", "").strip()
        query_terms = extract_terms(clean_query)
        
        if not query_terms:
            print("검색어가 없습니다.")
            return

        # 2. AND Query / Phrase Query일 경우: 모든 검색어가 포함된 문서 교집합(Candidate Docs) 구하기
        candidate_docs = None
        term_postings_map = {} # 포스팅 리스트 캐싱 (IO 줄이기)

        for term in query_terms:
            if term not in self.term_dict:
                if is_and_query: # AND 조건인데 단어가 없으면 결과 0개
                    candidate_docs = set()
                    break
                continue
            
            postings = self.get_postings(term)
            term_postings_map[term] = postings
            
            if is_and_query:
                # 필드 제약조건을 만족하는 문서 ID 집합 추출
                valid_docs_for_term = set()
                for doc_id, tf_title, tf_abstract, tf_claims in postings:
                    # 필드 조건 확인
                    is_in_field = False
                    if not target_fields: # 필드 명시 없으면 전체 필드 대상
                        is_in_field = True
                    else:
                        if "title" in target_fields and tf_title > 0: is_in_field = True
                        elif "abstract" in target_fields and tf_abstract > 0: is_in_field = True
                        elif "claims" in target_fields and tf_claims > 0: is_in_field = True
                    
                    if is_in_field:
                        valid_docs_for_term.add(doc_id)
                
                if candidate_docs is None:
                    candidate_docs = valid_docs_for_term
                else:
                    candidate_docs &= valid_docs_for_term # 교집합 연산
                    if not candidate_docs: # 교집합이 비면 조기 종료
                        break
        
        # Phrase Query 검증 (Exact Matching in Title)
        if is_phrase_query and candidate_docs:
            verified_docs = set()
            for doc_id in candidate_docs:
                doc_info = self.doc_table[doc_id]
                file_path = doc_info['path']
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        title = data['dataset'].get('invention_title', '')
                        if clean_query in title: # 원본 쿼리(clean_query)가 제목에 포함되어 있는지 확인
                            verified_docs.add(doc_id)
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
            candidate_docs = verified_docs

        if is_and_query and not candidate_docs:
            print(f'''RESULT:
              검색어: {query_terms} (AND/PHRASE)
              총 0개 문서 검색
              상위 5개 문서:
              ''')
            return

        # 3. BM25F 점수 계산
        w_title = 2.5 
        w_abstract = 1.5
        w_claims = 1.1

        b_title = 0.3 # 필드별 길이 정규화 세기
        b_abstract = 0.75
        b_claims = 0.8
        
        k1 = 1.2 # 파라미터 값 정의
        
        avgdl_title = sum(d['len_title'] for d in self.doc_table) / self.N
        avgdl_abstract = sum(d['len_abstract'] for d in self.doc_table) / self.N
        avgdl_claims = sum(d['len_claims'] for d in self.doc_table) / self.N
        # 필드별 평균 길이(토큰 수) 계산

        doc_scores = {} # 랭크 값 {[0, 15], [5, 12], ... }
        for term in query_terms:
            if term not in term_postings_map:
                if term in self.term_dict: # 캐싱 안된 경우 (OR 쿼리 등)
                    term_postings_map[term] = self.get_postings(term)
                else:
                    continue
            df = self.term_dict[term]["df"] # 데이터 의 df를 df에 저장
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1) # idf 계산식 ㅇ

            postings = term_postings_map[term]
            for doc_id, tf_title, tf_abstract, tf_claims in postings:
                # AND/Phrase 쿼리인 경우 교집합(및 검증된)에 있는 문서만 계산
                if is_and_query and doc_id not in candidate_docs:
                    continue
                
                doc = self.doc_table[doc_id]
                
                # 필드 제약조건 적용: 선택되지 않은 필드의 TF는 0으로 취급
                real_tf_title = tf_title if (not target_fields or "title" in target_fields) else 0
                real_tf_abstract = tf_abstract if (not target_fields or "abstract" in target_fields) else 0
                real_tf_claims = tf_claims if (not target_fields or "claims" in target_fields) else 0
                
                # 해당 문서에서 유효한 필드에 단어가 하나도 없으면 스킵 (OR 쿼리에서도 필드 제한 적용 가능)
                if real_tf_title == 0 and real_tf_abstract == 0 and real_tf_claims == 0:
                    continue

                # 필드별 TF 계산을 위한 분모 값.
                Bunmo_title = 1 - b_title + b_title * (doc['len_title'] / avgdl_title)
                Bunmo_abstract = 1 - b_abstract + b_abstract * (doc['len_abstract'] / avgdl_abstract)
                Bunmo_claims = 1 - b_claims + b_claims * (doc['len_claims'] / avgdl_claims)
                
                # sum( wf * tf_t,d,f / B_t,d,f )    
                tilde_tf = (w_title * real_tf_title / Bunmo_title) + \
                           (w_abstract * real_tf_abstract / Bunmo_abstract) + \
                           (w_claims * real_tf_claims / Bunmo_claims)
                
                # 최종 BM25F 점수 계산
                numerator = tilde_tf * (k1 + 1) # 분자
                denominator = k1 + tilde_tf # 분모
                
                bm25f_score = idf * (numerator / denominator) # 기존 idf랑 곱하기
                
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + bm25f_score
                # 랭킹 값이 doc_scores로 들어감. 
                # ex) {doc_id:BM25f_score} 101:0.5 가 들어오고 101:0.8이 또 들어오면 101:1.3이 되는 원리. term들이 겹칠수록 점수가 높아진다.
                
        # doc_scores의 상위 5개 문서를 추출해서 새로운 리스트로 만들자.
        sorted_doc_scores = sorted(doc_scores.items(), key = lambda x:x[1], reverse=True) # if_idf 높은순으로 정렬
        top5_doc_scores = sorted_doc_scores[:5] # 5개만 따로 리스트 만들기
        
        print(f'''RESULT:
                    검색어 입력: {user_query}
                    총 {len(doc_scores)}개 문서 검색
                    상위 {len(top5_doc_scores)}개 문서:''')
        
        for idx, score in top5_doc_scores:
            print(f'  {self.doc_table[idx]["filename"]}  {round(score,2)}')
            
        print("-" * 50)
        print()

        for idx, score in top5_doc_scores:
            print(f'파일명: {self.doc_table[idx]["filename"]}, 점수: {round(score,2)}')
            
            # [VERBOSE] 옵션이 있을 경우 하이라이팅 출력
            if "[VERBOSE]" in user_query:
                mode = "OR"
                if is_phrase_query: mode = "PHRASE"
                elif is_and_query: mode = "AND"
                
                # Phrase Query인 경우 원본 쿼리(clean_query)를 전달
                terms_to_highlight = [clean_query] if is_phrase_query else query_terms
                self.highlight_snippet(idx, terms_to_highlight, mode)
            print()

    def highlight_snippet(self, doc_id, query_terms, mode):
        doc_info = self.doc_table[doc_id]
        file_path = doc_info['path']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data['dataset'].get('invention_title', '')
                abstract = data['dataset'].get('abstract', '')
                claims = data['dataset'].get('claims', '')
        except Exception as e:
            print(f"Error reading file for highlighting: {e}")
            return

        # 검색 대상 텍스트 및 우선순위 설정
        # Title > Abstract > Claims 순서
        targets = [("TITLE", title), ("ABSTRACT", abstract), ("CLAIMS", claims)]
        
        window_size = 80
        
        if mode == "PHRASE":
            # Phrase Query: Title에서만 정확히 일치하는 한 곳만 출력
            if clean_query := query_terms[0]: # query_terms has [clean_query]
                 match = re.search(re.escape(clean_query), title, re.IGNORECASE)
                 if match:
                    idx = match.start()
                    start = max(0, idx - (window_size - len(clean_query)) // 2)
                    end = min(len(title), start + window_size)
                    snippet = title[start:end]
                    snippet = re.sub(re.escape(clean_query), fr"<<\g<0>>>", snippet, flags=re.IGNORECASE)
                    print(f"[{targets[0][0]}] {snippet}")
            return

        elif mode == "OR":
            # OR Query: 최대한 (서로 다른) query가 가장 많이 발생한 한 부분만 출력
            best_snippet = ""
            best_score = -1
            best_field = ""
            
            for field_name, text in targets:
                if not text: continue
                
                term_indices = []
                for term in query_terms:
                    for match in re.finditer(re.escape(term), text, re.IGNORECASE):
                        term_indices.append(match.start())
                
                if not term_indices: continue
                term_indices.sort()
                
                for start_idx in term_indices:
                    
                    w_start = max(0, start_idx - window_size // 2)
                    w_end = min(len(text), w_start + window_size)
                    window_text = text[w_start:w_end]
                    
                    current_score = 0
                    for term in query_terms:
                        if re.search(re.escape(term), window_text, re.IGNORECASE):
                            current_score += 1
                    
                    if current_score > best_score:
                        best_score = current_score
                        best_snippet = window_text
                        best_field = field_name
            
            if best_snippet:
                for term in query_terms:
                    best_snippet = re.sub(re.escape(term), fr"<<\g<0>>>", best_snippet, flags=re.IGNORECASE)
                print(f"[{best_field}] {best_snippet}")
                
        elif mode == "AND":
            # AND Query: 모든 term이 다 등장할 때까지 (여러 부분) 출력
            remaining_terms = set(query_terms)

            while remaining_terms:
                best_snippet = ""
                best_score = -1 
                best_field = ""
                covered_in_this_step = set()
                best_window_indices = (0, 0) # start, end
                best_text_ref = ""
                
                for field_name, text in targets:
                    if not text: continue
                    
                    
                    term_indices = []
                    for term in remaining_terms:
                         for match in re.finditer(re.escape(term), text, re.IGNORECASE):
                            term_indices.append(match.start())
                            
                    if not term_indices: continue
                    term_indices.sort()
                    
                    for start_idx in term_indices:
                        w_start = max(0, start_idx - window_size // 2)
                        w_end = min(len(text), w_start + window_size)
                        window_text = text[w_start:w_end]
                        
                        current_covered = set()
                        for term in remaining_terms:
                             if re.search(re.escape(term), window_text, re.IGNORECASE):
                                current_covered.add(term)
                        
                        if len(current_covered) > best_score:
                            best_score = len(current_covered)
                            best_snippet = window_text
                            best_field = field_name
                            covered_in_this_step = current_covered
                            best_window_indices = (w_start, w_end)
                            best_text_ref = text
                
                if best_score > 0:
                    
                    highlighted = best_snippet
                    for term in query_terms:
                         highlighted = re.sub(re.escape(term), fr"<<\g<0>>>", highlighted, flags=re.IGNORECASE)
                    
                    print(f"[{best_field}] {highlighted}")
                    
                    remaining_terms -= covered_in_this_step
                    
                    if not covered_in_this_step:
                        break
                else:
                    break