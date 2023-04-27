import pandas as pd
from requests import Session
from io import StringIO


def get_ucitele_katedry(username, password, origin_url, data_url, vars, column=None):
    with Session() as s:
        s.auth = (username, password)
        webove_sluzby_page = s.get(origin_url)
        response = s.get(data_url, headers={}, params=vars)
        # print(response.text)
        data = response.text
        df = pd.read_csv(StringIO(data), sep = ";")
    
    if column:
        return df[column]
    else:
        return df