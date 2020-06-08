from collections import namedtuple
PhraseContainer = namedtuple('PhraseContainer', ('value'))


class Node:
    def __init__(self):
        self.childs = dict()
        self.top_phrases = []
        
    def __repr__(self):
        return f'{self.childs}; {self.top_phrases}'

        
class Trie:
    TOP_PHRASES_PER_PREFIX = 5
    
    def __init__(self):
        self._root = Node()
        self._all_phrases = dict() # Flyweight pattern, in order to decrease duplication of phrase values
    
    def add_phrase(self, phrase):
        phrase = phrase.lower()
        node = self._root
        for c in phrase:
            if (c in node.childs):
                node = node.childs[c]
            else:
                new_node = Node()
                node.childs[c] = new_node
                node = new_node
                
            if (len(node.top_phrases) < Trie.TOP_PHRASES_PER_PREFIX):
                if (phrase not in self._all_phrases):
                    self._all_phrases[phrase] = PhraseContainer(phrase)
                node.top_phrases.append(self._all_phrases[phrase])
    
    def top_phrases_for_prefix(self, prefix):
        prefix = prefix.lower()
        node = self._root
        for c in prefix:
            if (c not in node.childs):
                return []
            node = node.childs[c]

        return [top_phrase.value for top_phrase in node.top_phrases]
