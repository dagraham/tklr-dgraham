The task entry string:

- dog house @s 2025-05-15
    @l lowes 
    @j paint &c shop
    @j   sand &c shop
    @j     assemble &c shop
    @j       cut pieces &c shop
    @j          get wood &c Lowes
    @j            go to Lowes &l lowes &c errands
    @j              get gas &c errands
    @j            create plan and parts list &l plan
    @j       get hardware &c Lowes
    @j         lowes
    @j         plan
    @j   get paint &c Lowes
    @j       lowes
    @j       plan

The tokenized version of the string

   [('-', 0, 1), ('dog house ', 2, 12), ('@s 2025-05-15\n    ', 12, 30), ('@j paint &c shop \n    ', 30, 52), ('@j   sand &c shop \n    ', 52, 75), ('@j     assemble &c shop \n    ', 75, 104), ('@j       cut pieces &c shop \n    ', 104, 137), ('@j          get wood &c Lowes\n    ', 137, 171), ('@j            go to Lowes &l lowes &c errands\n    ', 171, 221), ('@j              get gas &c errands\n    ', 221, 260), ('@j            create plan and parts list &l plan\n    ', 260, 313), ('@j       get hardware &c Lowes \n    ', 313, 349), ('@j         lowes\n    ', 349, 370), ('@j         plan\n    ', 370, 390), ('@j   get paint &c Lowes \n    ', 390, 419), ('@j       lowes\n    ', 419, 438), ('@j       plan\n    ', 438, 456)]



{'j': 'paint', 'c': 'shop', 'node': 0, 'itemtype': '+', 'subject': 'paint 3/6/0', 'i': 0}
{'j': 'sand', 'c': 'shop', 'node': 1, 'itemtype': '+', 'subject': 'sand 3/6/0', 'i': 1}
{'j': 'assemble', 'c': 'shop', 'node': 2, 'itemtype': '+', 'subject': 'assemble 3/6/0', 'i': 2}
{'j': 'cut pieces', 'c': 'shop', 'node': 3, 'itemtype': '+', 'subject': 'cut pieces 3/6/0', 'i': 3}
{'j': 'get wood', 'c': 'Lowes', 'node': 4, 'itemtype': '+', 'subject': 'get wood 3/6/0', 'i': 4}
{'j': 'go to Lowes', 'l': 'lowes', 'c': 'errands', 'node': 5, 'jl': 'lowes', 'itemtype': '+', 'subject': 'go to Lowes (lowes) 3/6/0', 'i': 5}
{'j': 'get gas', 'c': 'errands', 'node': 6, 'itemtype': '-', 'subject': 'get gas 3/6/0', 'i': 6}
{'j': 'create plan and parts list', 'l': 'plan', 'node': 5, 'jl': 'plan', 'itemtype': '-', 'subject': 'create plan and parts list (plan) 3/6/0', 'i': 7}
{'j': 'get hardware', 'c': 'Lowes', 'node': 3, 'itemtype': '-', 'subject': 'get hardware 3/6/0', 'i': 8}
{'j': 'lowes', 'itemtype': '?', 'subject': 'lowes 3/6/0', 'i': 9}
{'j': 'plan', 'itemtype': '?', 'subject': 'plan 3/6/0', 'i': 10}
{'j': 'get paint', 'c': 'Lowes', 'node': 1, 'itemtype': '?', 'subject': 'get paint 3/6/0', 'i': 11}
{'j': 'lowes', 'itemtype': '?', 'subject': 'lowes 3/6/0', 'i': 12}
{'j': 'plan', 'itemtype': '?', 'subject': 'plan 3/6/0', 'i': 13}
