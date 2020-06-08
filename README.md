# Implementation: Autocomplete/Typeahead Suggestions System Design

![Autocomplete Implementation System Design Intro Image](https://user-images.githubusercontent.com/3640622/89044441-e108b280-d341-11ea-8b12-974192c78773.png)

Implementation of a large scale autocomplete/typeahead suggestions system design, like the suggestions one gets when typing a Google search. Using Docker Compose.

More details **[in this blog article](https://lopespm.github.io/2020/08/03/implementation-autocomplete-system-design.html)**

## Requirements

Docker and Docker Compose are required to run this project.


## Usage

**Step 1** Run the system:

```bash
$ make run
```


**Step 2** Go to a different terminal. Add the basilar znodes and HDFS folders:
	
```bash
$ make setup
```


**Step 3** Send some phrases to the search endpoint, in order to simulate multiple user search submissions to the system. This way we will have a data starting point:

```bash
$ make populate_search
```


**Step 4** The map reduce tasks will reduce the top searches into a single HDFS file, which will be later transformed automatically by the system into a trie, and distributed to the backend:

```bash
$ make do_mapreduce_tasks
```

After the tries are distributed to the backend, please *wait about a minute* for the `trie-backend-applier` service to kick in. This service will assign the new backend nodes to receive the ensuing `top-phrases` requests.

**Step 5** Visit `http://localhost/` in your browser.

![Client Webpage](https://user-images.githubusercontent.com/3640622/89044611-1b724f80-d342-11ea-88e0-a9f04db33fda.png)

Write some text in the input form, and you should start to see some suggestions popping up.

You can also submit your search queries, which will be fed into the assembler. After you've submitted some entries, run `make do_mapreduce_tasks` again, and your queries will be considered for the next batch of suggestions. Enjoy!