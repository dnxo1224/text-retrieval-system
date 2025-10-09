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
                doc_id += 1 # 0번째 파일부터 시작.
                file_path = os.path.join(root, f) 
                doc_table.append({"doc_id": doc_id, "filename": f, "path": file_path}) # doc_table 제작
                with open(file_path, encoding='utf8') as f: # 파일 열기
                    data = json.load(f)
                    print(f"open file : {doc_id}")
                    text = data['dataset'].get('invention_title','') + " " + data['dataset'].get('abstract','') + " " + data['dataset'].get('claims','')
                    sorted_txt = extract_terms(text) # 규칙에 맞게 sort된 단어들 list.
                    
                    # 이제 단어들마다 딕셔너리를 만들어야함. 

                    # TF: term frequency (전체 문서 집합에서의 출현 빈도) / 문서 내 중복 값도 넣기
                    # DF: document frequency (몇 개의 문서에서 사용되었는가?) / 문서 내 중복 값은 하나로
                    
                    # 단어별 빈도수 딕셔너리 생성
                    txt_counts = {}
                    for txt in sorted_txt:
                        txt_counts[txt] = txt_counts.get(txt, 0) + 1 
                        # get으로 txt_counts[txt]의 value를 가져오고 + 1. txt라는 키가 안만들어져 있으면 0을 반환하고 + 1
                        # txt_counts[txt] += 1 <- 이렇게 해버리면 키가 없을때 KeyError를 반환.

                    # txt_counts 의 형태 : {"ai":3, "model:5", "data":7}
                    
                    for txt,txt_value in txt_counts.items(): # txt_counts에서 df, tf, posting_list 뽑아내기
                        if not txt in word_dic.keys():
                            word_dic[txt] = {"df" : 0, "tf" : 0, "posting_list" : []}
                            
                        word_dic[txt]["df"] += 1 # txt_counts에 txt가 존재하면 일단 해당 문서에 존재 했다는 것.

                        word_dic[txt]["tf"] += txt_value # txt_counts의 value값이 곧 해당 문서의 tf 값.

                        word_dic[txt]["posting_list"].append((doc_id,txt_value)) # doc_id 마다 txt_value 넣기

                    # word_dic 의 형태 : {
                    # "ai": {"df": 123, “tf”: 4567, “posting_list”:[(doc_0, 12), (doc_1, 34), (doc_23, 2), …] },
                    # "model":{"df": 256, “tf”: 12349, “posting_list”:[(doc_10, 164), (doc_13, 334), (doc_35, 22), …] },
                    # "data": {"df": 512,“tf”: 9831, “posting_list”:[(doc_5, 4), (doc_8, 84), (doc_9, 222), …] }, ...
                    # }
                    
        for word_dic_txt,word_dic_value in word_dic.items():
            term_postings[word_dic_txt] = word_dic_value["posting_list"]
        
        # postings.bin + term_dict.json 생성
        term_dict = {}
        offset = 0

        with open(self.postings_file,'wb') as pbin:
            for term, plist in term_postings.items():
                start = offset
                for doc_id, freq in plist:
                    pbin.write(struct.pack("ii", doc_id, freq))
                    offset += 8
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