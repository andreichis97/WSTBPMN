from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE, N3, CSV
from access_keys import key_openai
import os
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = key_openai

client = OpenAI()

read_file = open("D:\\Andrei\\ModellingTools\\WST_BPMN_Modeling_Tool\\Results\\graphrag_query.txt", "r")
lines = read_file.readlines()
# Set the repository ID and graph URI
repository_id = lines[0].strip()
query = lines[2].strip()
read_file.close()

def get_query_subjects(user_query):
    prefilled_prompt_sys_claude = """
    You are an advanced language analysis assistant specializing in subject identification within sentences or phrases. Your task is to accurately identify and categorize subjects in any given text.
    Instructions:
    1. Carefully read and analyze the input text.
    2. Identify all potential subjects in the text. Subjects can include, but are not limited to:
    - People (individuals, groups, professions)
    - Entities (companies, institutions, brands)
    - Organizations (governments, non-profits, associations)
    - Businesses (corporations, small businesses, startups)
    - Locations (countries, cities, landmarks, geographical features)
    - Systems (political systems, ecosystems, technological systems)
    - Laws (regulations, policies, legal concepts)
    - Elements of infrastructure (buildings, roads, utilities)
    - Abstract concepts (ideas, theories, philosophies)
    - Natural phenomena (weather events, geological processes)
    - Animals and plants (species, habitats)
    - Time periods (historical eras, seasons, dates)

    3. Consider the context of the text to ensure accurate subject identification, especially in cases of ambiguity or multiple interpretations.

    4. Categorize each identified subject based on the most appropriate category from the list above or a relevant subcategory.
    """
    prefilled_prompt_user1 = "You will extract the subjects from the following phrase or sentence: "
    prefilled_prompt_user2_claude = """
    Instructions:
    1. Carefully read the input phrase.
    2. Identify the main subject entities mentioned in the phrase.
    3. Create a list of these subject entities.
    4. Format the output as a Python list assignment, like ['subject1', 'subject2', 'subject3'] without any other annotations or text.
        Please follow these guidelines:
    - Include only unique subject entities in your list.
    - Do not include any additional text or explanations in your output, just the Python list assignment.

    Examples:
    Phrase1: What is the relationship between John and Mary?
    Output1: ['John', 'Mary']

    Phrase2: What is the relationship between Work System WS1 and Environment Element Elem1? What are work systems are related to Elem1?"
    Output2: ['WS1', 'Elem1']

    Phrase3: Give me information about the decomposition of Work System WS15. What relationship is between WS15 and Environment Element ElemEnv2? What relationship is between WS15 and Infrastructure Element Serv3?"
    Output3: ['WS15', 'ElemEnv2', 'Serv3']
    """
    user_prompt = prefilled_prompt_user1 + user_query + prefilled_prompt_user2_claude
    
    response = client.chat.completions.create(
        model="o1",
        messages=[
            {"role": "system", "content": prefilled_prompt_sys_claude},
            {"role": "user", "content": user_prompt}
        ],
    )
    message = response.choices[0].message.content
    return message

def check_type(label_to_check, repository):
    endpoint_url = f"""http://localhost:7200/repositories/{repository}"""
    sparql = SPARQLWrapper(endpoint_url)
    graph_query_type_check = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?type
    WHERE {
        ?entity rdfs:label """ + "'" + label_to_check + "'" + """;
            a ?type.
    }
    """
    sparql.setQuery(graph_query_type_check)
    sparql.setReturnFormat(JSON)
    res = sparql.queryAndConvert()
    element_types = res["results"]["bindings"]

    #print(element_types)

    for i in element_types:
        type_uri = i["type"]["value"]
        exists = type_uri.find("WorkSystemSnapshot")
        #print(exists)
        if exists > -1:
            return "WorkSystemSnapshot", type_uri
        else:
            return "None", type_uri

    #se ia din binding, apoi de la #incolo
    #cand se ia subgraful se trimite tot value
    #{'head': {'vars': ['type']}, 'results': {'bindings': [{'type': {'type': 'uri', 'value': 'http://www.example.org#Package'}}, {'type': {'type': 'uri', 'value': 'http://www.example.org#ComplexWSTElement'}}]}}

def extract_related_subgraph(label):
    snapshot_get_decomposition_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://www.example.org#>
    SELECT ?graphUri
    WHERE
    {
        ?s rdfs:label""" + "'" + label + "'" + """;
            :decomposedIn ?graphUri.
    }
    """
    sparql.setQuery(snapshot_get_decomposition_query)
    sparql.setReturnFormat(JSON)
    res = sparql.queryAndConvert()
    subgraph_uri = res["results"]["bindings"][0]["graphUri"]["value"]
    #print(subgraph_uri)
    
    snapshot_graph_query = """
    SELECT ?s ?p ?o
    WHERE
    {
        GRAPH <""" + subgraph_uri + """> {
            ?s ?p ?o
            }
    }
    """
    sparql.setQuery(snapshot_graph_query)
    sparql.setReturnFormat(JSON)
    subgraph = sparql.queryAndConvert()

    subgraph_triples = ""
    for i in subgraph["results"]["bindings"]:
        s = i["s"]["value"]
        p = i["p"]["value"]
        o = i["o"]["value"]
        triple = "<" + s + ">" + " " + "<" + p + ">" + " " + "<" + o + ">" + " .\n"
        subgraph_triples = subgraph_triples + triple

    return subgraph_triples, subgraph_uri

def extract_graph_chunks(subjects, repository):
    #endpoint_url = f"""http://localhost:7200/repositories/{repository}"""
    #sparql = SPARQLWrapper(endpoint_url)
    labels_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label
    WHERE {
        ?x rdfs:label ?label
    }
    """
    sparql.setQuery(labels_query)
    sparql.setReturnFormat(JSON)
    results = sparql.queryAndConvert()
    #print(results)
    labels = []
    kg_context = ""
    length = len(results["results"]["bindings"])

    for i in range(0, length):
        labels.append(results["results"]["bindings"][i]["label"]["value"])
    
    subgraph_context = ""
    for i in subjects:
        if i in labels:
            graph_query = """
            PREFIX : <http://www.example.org#>
            CONSTRUCT 
            {
                ?lookingFor ?relation1 ?ob.
                ?ob ?relation2 ?lookingFor.
            }
            WHERE
            {
                {
                    ?lookingFor rdfs:label """ + "'" + i + "'" + """; 
                        ?relation1 ?ob. 
                }
                UNION
                {
                    ?ob ?relation2 ?lookingFor.
                    ?lookingFor rdfs:label """ + "'" + i + "'" + """.
                }
            }"""
            sparql.setQuery(graph_query)
            sparql.setReturnFormat(N3)
            results = sparql.queryAndConvert().decode("utf-8")
            #print(results)

            element_type, graph_uri = check_type(i, repository)
            #print(element_type)
            #print("GRAPH URI: ")
            #print(element_type)
            #print(graph_uri)
            #print("--------------------------------------------")

            if element_type == "WorkSystemSnapshot":
                subgraph, subgraph_uri = extract_related_subgraph(i)
                subgraph_context = "\n" + subgraph_context + "<" + subgraph_uri + ">" + " is composed of the following triples: \n"
                #print(subgraph)
                subgraph_context = subgraph_context + subgraph

            kg_context = kg_context + results + subgraph_context    
    
    return kg_context

"""def query_ai_model(context, user_query):
    sys_prompt = "You are a helpful assistant specialized in analyzing systems and work systems. You are given a knowledge graph in Turtle format, with a few text annotations, that you will have to analyze every time. Each time, you will base your answer solely on the given knowledge graph extract without external information."
    user_query_to_model = user_query + " The context you will base your answer on is: " + context
    response = ollama.chat(model="llama3.1", options={"temperature":0}, 
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_query_to_model}
            ],           
        )
    return response["message"]["content"]"""

def gather_all_kg(repository):
    endpoint_url = f"""http://localhost:7200/repositories/{repository}"""
    sparql = SPARQLWrapper(endpoint_url)
    query = """
    SELECT ?x ?y ?z
    WHERE {
        ?x ?y ?z
    }
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.queryAndConvert()
    return str(results)

def query_with_gpt(context, user_query):
    sys_prompt = "You are a helpful assistant specialized in analyzing systems and work systems. You are given a knowledge graph in Turtle format, with a few text annotations, that you will have to analyze every time. Each time, you will base your answer solely on the given knowledge graph extract without external information."
    user_query_to_model = user_query + " The context you will base your answer on is: " + context
    response = client.chat.completions.create(
        model="o1",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_query_to_model}
        ],
    )
    message = response.choices[0].message.content
    return message

def main():
    
    global repository
    global sparql
    
    repository = repository_id

    endpoint_url = f"""http://localhost:7200/repositories/{repository}"""
    sparql = SPARQLWrapper(endpoint_url)
    
    prompt = query
    response = get_query_subjects(prompt)

    subjects = eval(response)

    context = extract_graph_chunks(subjects, repository)

    print("-------Graph results------\n")
    if(context == ""):
        context = gather_all_kg(repository)
        
    print(context)

    #final_response = query_ai_model(context, prompt)
    final_response_gpt = query_with_gpt(context, prompt)

    print("FINAL RESPONSE GPT: \n")
    print(final_response_gpt)

    write_file = open("D:\\Andrei\\ModellingTools\\WST_BPMN_Modeling_Tool\\Results\\graphrag_results.txt", "w")
    write_file.write(final_response_gpt)

    write_file.close()

main()