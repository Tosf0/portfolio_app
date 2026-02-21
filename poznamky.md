# Overall
- Jedná se o mé první využití frameworku Django, využití přístupu na LLM API.

## Vstupní data
- Formát vstupních dat není zcela ideální a obsahuje zbytečně mnoho opakujících se hodnot,
bylo by vhodné data normalizovat.
- Validace hlídá povinná pole, datové typy, detekuje prázdné řetězce a hlídá "povolené hodnoty" u vybraných polí, ale nehlídá logickou správnost dat (např. datum vyřazení je menší než datum spuštění, jména) ani není hlídána unikátnost dat.

## Django
- 