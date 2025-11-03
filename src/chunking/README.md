# Chunking Strategy

<img src="./docs/chunking_logic.png" alt="Propositioner Model" width="600">



  
## Data Preprocess Pipeline on EURLEX Data
## Table of Contents
- [Example of Data Preprocess Pipeline on EURLEX Data](#example-of-data-preprocess-pipeline-on-eurlex-data)
  - [Original Text](#original-text)
  - [Proposition Model](#proposition-model)
    - [Meaning Comparison](#meaning-comparison)
  - [Semantic Splitting](#semantic-splitting)



### Original Text : 

Original text looks like this. 


> Having regard to Article 83 of the Treaty establishing the European Economic Community, which provides that an advisory committee consisting of experts designated by the Governments of Member States shall be attached to the Commission and consulted by the latter on transport matters whenever the Commission considers this desirable, without prejudice to the powers of the transport section of the Economic and Social Committee; Having regard to Article 153 of that Treaty, which provides that the Council shall, after receiving an opinion from the Commission, determine the rules governing the committees provided for in that\n\nTreaty;\n\nHaving received an Opinion from the Commission;\n\n## Main Body:\n\nthat the Rules of the Transport Committee shall be as follows:\n\nThe Committee shall consist of experts on transport matters designated by the Governments of Member States. Each Government shall designate one expert or two experts selected from among senior officials of the central administration. It may, in addition, designate not more than three experts of acknowledged competence in, respectively, the railway, road transport and inland waterway sectors.\n\nEach Government may designate an alternate for each member of the Committee appointed by it; this alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.\n\nAlternates shall attend Committee meetings and take part in the work of the Committee only in the event of full members being unable to do so.\n\nCommittee members and their alternates shall be appointed in their personal capacity and may not be bound by any mandatory instructions.\n\nThe term of office for members and their alternates shall be two years. Their appointments may be renewed.\n\nIn the event of the death, resignation or compulsory retirement of a member or alternate, that member or alternate shall replaced for the remainder of his term of office.\n\nThe Government which appointed a member or alternate may compulsorily retire that member or alternate only if the member or alternate no longer fulfils the conditions required for the performance of his duties.\n\nThe Committee shall, by an absolute majority of members present and voting, elect from among the members appointed by virtue of their status as senior officials of the central administration a Chairman and Vice-Chairman, who shall serve as such for two years. Should the Chairman or Vice-Chairman cease to hold office before the period for which he was elected has expired, a replacement for him shall be elected for the remainder of the period for which he was originally elected.\n\nNeither the Chairman nor the Vice-Chairman may be re-elected.\n\nThe Committee shall be convened by the Chairman, at the request of the Commission, whenever the latter wishes to consult it. The Commission's request shall state the purpose of the consultation.\n\nWhen the Committee is consulted by the Commission, it shall present the latter with a report setting out the conclusions reached as a result of its deliberations. It shall do likewise if the Commission entrusts it with the study of a specific problem. The Commission shall also be entitled to consult the Committee orally. The minutes of the Committee shall be sent to the Commission.\n\nThe Commission shall be invited to send its representatives to meetings of the Committee and its working parties.\n\nThe Committee shall, by an absolute majority of members present and voting, adopt rules of procedure laying down its methods of working.\n\nThe Committee may, whenever such action appears to it to be necessary for the purposes of formulating an opinion, seek the assistance of any suitably qualified person, obtain any advice and hold hearings. Such action may, however, be taken only with the consent of the Commission.\n\n0\n\nThe expenses of the Committee shall be included in the estimates of the Commission.\n\n## Attachments:\n\nDone at Brussels, 15 September 1958.\n\nFor the Council The President L. Erhard



### Proposition Model

As explained on README.md, proposition model express pronouns in descriptive way. Marked, it shows the changes between original and modified.


| **Original Legal Text** | **Propositionized Output** |
|--------------------------|-----------------------------|
| *Having regard to <mark>Article 83</mark> of the Treaty establishing the European Economic Community, which provides that an advisory committee consisting of experts designated by the Governments of Member States shall be attached to the Commission and consulted by the latter on transport matters whenever the Commission considers this desirable, without prejudice to the powers of the transport section of the Economic and Social Committee;* | **<mark>Article 83</mark> of the Treaty establishing the European Economic Community <mark>provides for</mark> an advisory committee consisting of experts designated by the Governments of Member States.**  <br> **The advisory committee shall be attached to the Commission and consulted on transport matters whenever the Commission considers it desirable.**  <br> **The advisory committee shall not prejudice the powers of the transport section of the Economic and Social Committee.** |
| *Having regard to <mark>Article 153</mark> of that Treaty, which provides that the Council shall, after receiving an opinion from the Commission, determine the rules governing the committees provided for in that Treaty;* | **<mark>Article 153</mark> of the Treaty <mark>provides for the Council to determine</mark> the rules governing the committees provided for in that Treaty after receiving an opinion from the Commission.** |
| *Having <mark>received</mark> an Opinion from the Commission;* | ⚠️ **The Council <mark>shall receive</mark> an Opinion from the Commission.** |
| *That the Rules of the Transport Committee <mark>shall be as follows</mark>:* | ⚠️ **The Rules of the Transport Committee <mark>shall consist of experts on transport matters designated by the Governments of Member States</mark>.** |
| *The Committee shall consist of experts on transport matters designated by the Governments of Member States.* | **<mark>Each Government shall designate one expert or two experts selected from among senior officials of the central administration.</mark>** |
| *It may, in addition, designate not more than three experts of acknowledged competence in, respectively, the railway, road transport and inland waterway sectors.* | **Each Government may designate not more than three experts of acknowledged competence in the <mark>railway, road transport, and inland waterway</mark> sectors.** |
| *Each Government may designate an alternate for each member of the Committee appointed by it; this alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.* | **Each Government may designate an alternate for each member of the Committee appointed by it.**  <br> **The alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.** |
| *Committee members and their alternates shall be appointed in their personal capacity and may not be bound by any mandatory instructions.* | **Committee members and their alternates shall be appointed in their personal capacity.** <br> **Committee members and their alternates may not be bound by any mandatory instructions.** |
| *The term of office for members and their alternates shall be two years. Their appointments may be renewed.* | **The term of office for members and their alternates shall be two years.** <br> **<mark>Appointments for members and their alternates may be renewed.</mark>** |
| *In the event of the death, resignation or compulsory retirement of a member or alternate, that member or alternate shall <mark>replaced</mark> for the remainder of his term of office.* | **In the event of the death, resignation, or compulsory retirement of a member or alternate, that member or alternate shall <mark>be replaced</mark> for the remainder of his term of office.** |



#### Meaning Comparison

For the example, not in the pipeline, I used ChatGPT to check if modifications change any meaning, it seems our proposition model works well.


| Clause | Original intention | Propositionized version | Meaning change |
|--------|--------------------|--------------------------|----------------|
| “Having regard to Article 83…” | Cites the legal authority and basis. | Declarative factual statement of Article 83’s content. | ✅ No change (stylistic only). |
| “Attached to the Commission…” | Defines advisory linkage to Commission. | Rephrased identically. | ✅ Same meaning. |
| “Without prejudice…” | Ensures existing powers remain. | Restated identically. | ✅ Same meaning. |
| “Having regard to Article 153…” | Cites second authority. | Declarative factual restatement. | ✅ Same meaning. |
| “Having received an Opinion…” | Indicates past procedural completion. | “Shall receive” — shifts to normative future tense. | ⚠️ Minor temporal nuance change. |
| “That the Rules… shall be as follows” | Introduces forthcoming section. | Compressed into direct declarative of rule content. | ⚠️ Slight formal change, semantics intact. |
| Membership / alternates / term clauses | Normative rules about composition and duration. | Split into clear, one-sentence propositions. | ✅ Same meaning, better granularity. |




### Semantic Splitting


Proposed model proposes the text. 

And in late chunking, pipeline checks if meaning shift between sentences exists.

Logic follows the diagram.

<img src="./docs/late_chunking.png" alt="Propositioner Model" width="300">


Any sudden change on the different between vector embeddings, code defines a breakpoint, then chunking between breakpoints. 

As you'll see in example, it makes sense!!!


Final output via late chunking is :


>1. Article 83 of the Treaty establishing the European Economic Community provides for an advisory committee consisting of experts designated by the Governments of Member States. The advisory committee shall be attached to the Commission and consulted on transport matters whenever the Commission considers it desirable. The advisory committee shall not prejudice the powers of the transport section of the Economic and Social Committee.


>2. Article 153 of the Treaty provides for the Council to determine the rules governing the committees provided for in that Treaty after receiving an opinion from the Commission. The Council shall receive an Opinion from the Commission. The Rules of the Transport Committee shall consist of experts on transport matters designated by the Governments of Member States. Each Government shall designate one expert or two experts selected from among senior officials of the central administration. Each Government may designate not more than three experts of acknowledged competence in the railway, road transport, and inland waterway sectors. Each Government may designate an alternate for each member of the Committee appointed by it. The alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.


>3. Alternates shall attend Committee meetings and take part in the work of the Committee only in the event of full members being unable to do so. Committee members and their alternates shall be appointed in their personal capacity. Committee members and their alternates may not be bound by any mandatory instructions. The term of office for members and their alternates shall be two years. Appointments for members and their alternates may be renewed. In the event of the death, resignation, or compulsory retirement of a member or alternate, that member or alternate shall be replaced for the remainder of his term of office. The Government which appointed a member or alternate may compulsorily retire that member or alternate only if the member or alternate no longer fulfils the conditions required for the performance of his duties. The Committee shall elect a Chairman and Vice-Chairman from among the members appointed by virtue of their status as senior officials of the central administration. The Chairman and Vice-Chairman shall serve as such for two years. Should the Chairman or Vice-Chairman cease to hold office before the period for which he was elected has expired, a replacement for him shall be elected for the remainder of the period for which he was originally elected. Neither the Chairman nor the Vice-Chairman may be re-elected. The Chairman shall convene the Committee at the request of the Commission whenever the latter wishes to consult it.

>4. The Commission's request shall state the purpose of the consultation.

>5. When the Committee is consulted by the Commission, it shall present the Commission with a report setting out the conclusions reached as a result of its deliberations. The Committee shall present the Commission with a report if the Commission entrusts it with the study of a specific problem. The Commission shall also be entitled to consult the Committee orally. The minutes of the Committee shall be sent to the Commission. The Commission shall be invited to send its representatives to meetings of the Committee and its working parties. The Committee shall adopt rules of procedure laying down its methods of working. The Committee may seek the assistance of any suitably qualified person, obtain any advice and hold hearings. Such action may be taken only with the consent of the Commission. The expenses of the Committee shall be included in the estimates of the Commission.

>6. The President of the Council is L. Erhard.


