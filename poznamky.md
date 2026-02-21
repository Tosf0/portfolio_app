# Overall
- Jedná se o mé první využití frameworku Django, využití přístupu na LLM API.
- Aplikace je vyvíjena s pomocí modelů Claude (Opus, Sonnet) a to především k lepší orientaci v novém frameworku a jeho využití. Struktura projektu se tak primárně odráží od doporučení LLM.

## Vstupní data
- Formát vstupních dat není zcela ideální a obsahuje zbytečně mnoho opakujících se hodnot,
bylo by vhodné data normalizovat.
- Validace hlídá povinná pole, datové typy, detekuje prázdné řetězce a hlídá "povolené hodnoty" u vybraných polí, ale nehlídá logickou správnost dat (např. datum vyřazení je menší než datum spuštění, jména) ani není hlídána unikátnost dat (automaticky se hlídá pouze unikátnost ID).
- Prvotní pokus o načtení dat byl pomocí samostatné classy, která načítala jak vstupní json data, tak i json "template", který specifikoval parametry pro validaci a import dat. Tento přístup byl ale opuštěn ve prospěch navázání funkčnosti na struktury Django.

## Dashboard
- 