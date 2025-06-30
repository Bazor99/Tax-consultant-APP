from server.tools import agent

while True:
    query = input("User: ")
    if query in ("exit","quit"):
        break
    answer = agent.run(query)
    print("Assistant:", answer)