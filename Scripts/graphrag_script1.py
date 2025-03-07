import ollama
import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE, N3, CSV
#from pydantic import BaseModel

#class Subject(BaseModel):
#    subjectName: str

#class SubjectsList(BaseModel):
#    subjects: list[Subject]

def get_query_subjects(user_query):
    prefilled_prompt_sys = "You are a helpful assistant skilled in identifying the subjects in any sentence or phrase. The subjects of a sentence or phrase usually refer to people, entities, organizations, businesses, locations, systems, laws or elements of infrastructure." 
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
    #- The list should be named "subjects" in any case.
    prefilled_prompt_user1 = "You will extract the subjects from the following phrase or sentence: "
    #prefilled_prompt_user2 = "Provide the results in list format, matching the structure of the SubjectsList model: subjects: the list of subjects in the given sentence or phrase."
    prefilled_prompt_user2 = "Provide the results in a list format. For example, if the phrase is What is the relationship between John and Mary, the response should be subjects = ['John', 'Mary']. If the phrase is: What is the relationship between Work System WS1 and Environment Element Elem1? What are work systems are related to Elem1?, the response should be subject = ['WS1', 'Elem1'].  Provide the response without any additional text."
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

    response = ollama.chat(model="llama3.1", options={"temperature":0}, 
            messages = [
                {"role": "system", "content": prefilled_prompt_sys_claude},
                {"role": "user", "content": user_prompt}
            ],           
        )
    return response["message"]["content"]

def extract_graph_chunks(subjects, repository):
    endpoint_url = f"""http://localhost:7200/repositories/{repository}"""
    sparql = SPARQLWrapper(endpoint_url)
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
            sparql.setReturnFormat(TURTLE)
            results = sparql.queryAndConvert()
            #print(results)
            #g = rdflib.Graph()
            #g.parse(results, format="turtle")
            #entities = [str(s) for s in g.subjects()]
            #print(entities)
            kg_context = kg_context + str(results)    
    
    return kg_context

def query_ai_model(context, user_query):
    sys_prompt = "You are a helpful assistant specialized in analyzing systems and work systems. You are given a knowledge graph in Turtle format, that you will have to analyze every time. Every time, you will base your answer solely on the given knowledge graph extract without external information."
    user_query_to_model = user_query + " The context you will base your answer on is: " + context
    response = ollama.chat(model="llama3.1", options={"temperature":0}, 
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_query_to_model}
            ],           
        )
    return response["message"]["content"]


def main():
    prompt = input("Input a sentence: ")
    response = get_query_subjects(prompt)
    print(response)

    subjects = eval(response)
    print(subjects[0])

    repository = "WSTModelingTool"

    context = extract_graph_chunks(subjects, repository)

    print("-------Graph results------\n")
    print(context)

    final_response = query_ai_model(context, prompt)

    print("FINAL RESPONSE: \n")
    print(final_response)

main()