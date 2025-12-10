# src/indexer.py

import os
import json
import struct
from .tokenizer import extract_terms # tokenizer에 있는 추출 함수 가져오기. ps. 같은 디렉토리에 있기때문에 .tokenizer라고 써야함 !

class Indexer:
    def __init__(self, data_dir, output_dir, doc_table_file, term_dict_file, postings_file):
        self.data_dir = os.path.abspath(data_dir)
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.doc_table_file = os.path.join(self.output_dir, doc_table_file)
        self.term_dict_file = os.path.join(self.output_dir, term_dict_file)
        self.postings_file = os.path.join(self.output_dir, postings_file)
        
    def build_index(self):
        word_dic = {}
        term_postings = {}
        sorted_txt = []
        doc_id = -1 # 파일의 id를 추적하기 위한 변수 생성
        doc_table = []
        
        doc_id = -1 # id 초기화
        for root, dirs, files in os.walk(self.data_dir): # .walk로 파일 위치 받아오기
            for f in files: #f에는 파일 이름. 
                if not f.endswith('.json'):
                    print("not json")
                    continue
                file_path = os.path.join(root, f) 
                with open(file_path, encoding='utf8') as json_file: # 파일 열기
                    try:
                        data = json.load(json_file)
                    except json.JSONDecodeError:
                        print(f"Skipping malformed JSON file: {json_file.name}")
                        continue
                        
                    doc_id += 1 # 성공적으로 읽은 경우에만 doc_id 증가
                    print(f"open file : {doc_id}")

                    # 필드별 텍스트 추출 (이미 리스트 형태임)
                    title_txt = extract_terms(data['dataset'].get('invention_title',''))
                    abstract_txt = extract_terms(data['dataset'].get('abstract',''))
                    claims_txt = extract_terms(data['dataset'].get('claims',''))

                    # doc_table에 필드별 길이 저장
                    
                    doc_table.append({
                        "doc_id": doc_id,
                        "filename": f,
                        "path": file_path,
                        "len_title": len(title_txt),
                        "len_abstract": len(abstract_txt),
                        "len_claims": len(claims_txt)
                    })

                    # 단어별, 필드별 빈도수 계산
                    # txt_counts 구조: { "term": {"title": 0, "abstract": 0, "claims": 0} }
                    txt_counts = {}
                    
                    for t in title_txt:
                        if t not in txt_counts: txt_counts[t] = {"title": 0, "abstract": 0, "claims": 0}
                        txt_counts[t]["title"] += 1
                        
                    for t in abstract_txt:
                        if t not in txt_counts: txt_counts[t] = {"title": 0, "abstract": 0, "claims": 0}
                        txt_counts[t]["abstract"] += 1
                        
                    for t in claims_txt:
                        if t not in txt_counts: txt_counts[t] = {"title": 0, "abstract": 0, "claims": 0}
                        txt_counts[t]["claims"] += 1

                    for txt, fields_tf in txt_counts.items():
                        if txt not in word_dic:
                            word_dic[txt] = {"df": 0, "tf": 0, "posting_list": []}
                        
                        word_dic[txt]["df"] += 1
                        # 전체 TF는 단순 합 (BM25F에서는 개별 필드 TF가 중요하지만, 통계용으로 합쳐둠)
                        total_tf = fields_tf["title"] + fields_tf["abstract"] + fields_tf["claims"]
                        word_dic[txt]["tf"] += total_tf
                        
                        # posting_list에 (doc_id, tf_title, tf_abstract, tf_claims) 저장
                        word_dic[txt]["posting_list"].append((doc_id, fields_tf["title"], fields_tf["abstract"], fields_tf["claims"]))
                    
        for word_dic_txt,word_dic_value in word_dic.items():
            term_postings[word_dic_txt] = word_dic_value["posting_list"]
        
        # postings.bin + term_dict.json 생성
        term_dict = {}
        offset = 0

        with open(self.postings_file,'wb') as pbin:
            for term, plist in term_postings.items():
                start = offset
                for doc_id, tf_title, tf_abstract, tf_claims in plist: # 필드별로 나눠야 함. 
                    pbin.write(struct.pack("iiii", doc_id, tf_title, tf_abstract, tf_claims)) 
                    offset += 16 # postings.bin에 16바이트씩 쓰기 4바이트 값 4개 -> 16바이트임.
                term_dict[term] = {
                    "df": len(plist),
                    "start": start,
                    "length": len(plist)
                }
            print('postings_file 완료')

        with open(self.term_dict_file,'w',encoding='utf8') as f: # term_dict 파일로 write하기
            json.dump(term_dict, f, ensure_ascii=False,indent=4)
            print('term_dict_file 완료')
        
        with open(self.doc_table_file,'w',encoding='utf8') as f:
            json.dump(doc_table, f, ensure_ascii=False,indent=4)
            print('doc_table_file 완료')