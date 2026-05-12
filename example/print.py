from margrete_rpc import Margrete, Note

mg = Margrete("127.0.0.1:48731")
print(mg.ping())

with mg.open_edit("manual append") as tx:
    for x in tx.chart.notes:
        print(x)