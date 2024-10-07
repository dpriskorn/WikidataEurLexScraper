# #https://pypi.org/project/pyeurlex/
# import pandas as pd
#
# from eurlex.eurlex import Eurlex
# eur = Eurlex()
# q = eur.make_query(resource_type = "directive", order = True, limit = 10, include_date_endvalid=True, include_force=True, include_date_force=True)
# print(q)
# d = eur.query_eurlex(q)  # where q is a query generated in a previous step or a string defined by you
# d.to_csv(path_or_buf="test.csv")
# pd.set_option('display.max_colwidth', None)  # Set to display the full content of columns without truncation
# print(d)>