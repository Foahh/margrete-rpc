from margrete_rpc import Margrete

mg = Margrete("127.0.0.1:48731")
print("mg.ping(): ", mg.ping())

with mg.open_edit("manual append") as tx:
    print("tx.current_tick:", tx.current_tick)
    print("\n")
    for x in tx.chart.notes:
        print(x)
    print("\n")
    for x in tx.chart.events.bpm:
        print(x)
    print("\n")
    for x in tx.chart.events.beat:
        print(x)
    print("\n")
    for x in tx.chart.events.til:
        print(x)
    print("\n")
    for x in tx.chart.events.note_speed:
        print(x)
