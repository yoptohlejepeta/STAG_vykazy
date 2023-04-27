import pandas as pd
from requests import Session
from io import StringIO


def get_ucitele_katedry(username, password, origin_url, data_url, vars, column=None):
    """_summary_

    Args:
        username (_type_): _description_
        password (_type_): _description_
        origin_url (_type_): _description_
        data_url (_type_): _description_
        vars (_type_): _description_
        column (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
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