# JEThKnowledgeGraph

A simple Python tool to convert articles published in JETh format into a knowledge Graph.

# Features

* Parses PDF for Title/Author and citations using anystyle.
* Queries IXTheo for Keywords

# Usage

After storing all PDFs in the filesystem (Format: /Journal/Year/Issue/*.pdf), you can execute the tool as follows:

``` 
python3 buildGraph.py -i /tmp/Input/ -o /tmp/testn.graphml
```

To avoid the output, use ```---verbose``` or ```-v```. -c will avoid citations and -x will not query IXTheo.

Feel free to adjust the Black/Whitelists in bwlists.py to improve the quality.

# Things to do...

There are still some issues to solve. For example:


# Further information

pySNA is licensed under the GNU General Public License v3.0.
