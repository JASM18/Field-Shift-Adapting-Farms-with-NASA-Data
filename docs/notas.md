# Notas del proyecto, paso a paso

## ¿Qué pide el reto? (Field Shift)

En palabras simples:

> Los agricultores tienen que decidir **qué sembrar en cada temporada**. Hoy es más difícil
> porque el clima está cambiando (más calor, lluvias raras, menos agua) y el suelo se va desgastando.
> Quieren una app que les ayude a decidir usando **datos de satélites de la NASA**.

**Objetivo:** una aplicación para que los agricultores tomen decisiones.

### Concepto clave: rotación de cultivos

No sembrar siempre lo mismo en el mismo terreno, sino ir cambiando. Ejemplo:

- **Año 1:** maíz, que gasta muchos nutrientes del suelo
- **Año 2:** frijol, que le devuelve nitrógeno al suelo
- **Año 3:** otra vez maíz, y el suelo ya se recuperó

Si siembras maíz todos los años, el suelo se cansa, aparecen más plagas y necesitas más fertilizante.
La app debe ayudar a elegir una buena secuencia según el clima, el suelo y lo que el agricultor quiera.

## El camino, en pasos pequeños

1. Entender el problema
2. Entender qué información da cada dataset de la NASA, uno por uno
3. Decidir cuáles datasets nos sirven
4. Definir qué hará la app (qué pregunta y qué responde)
5. Construirla poco a poco

## Pregunta de investigación ✅ (decidida)

> ¿Cómo pueden los agricultores de regiones con climas extremos decidir qué sembrar, cuándo y cómo
> rotar sus cultivos para reducir pérdidas de cosecha por sequía y calor extremo?

(Versión anterior: "...para reducir pérdidas de cosecha y maximizar la calidad de los cultivos?".
Se cambió "calidad" por algo más concreto: sequía y calor extremo.)

Se divide en tres decisiones que la app debe apoyar:

- **¿Qué sembrar?** → cultivos que aguanten el clima de la zona
- **¿Cuándo sembrar?** → la mejor temporada según lluvia y temperatura
- **¿Cómo rotar?** → el orden de cultivos que cuide el suelo

Aclaraciones:

- **Alcance global, no solo México** (recomendación de la asesora): si el proyecto gana, debe
  servir para cualquier parte del mundo. Los datos de la NASA son globales, así que se puede.
  Para la demo podemos mostrar ejemplos de varias regiones con climas extremos.
- **"Calidad de los cultivos"** resume una versión anterior de la pregunta: "para reducir pérdidas
  de cosecha por **sequía y calor extremo** que terminan en **escasez y alza de precios** de los
  alimentos". Es decir: el enfoque está en la sequía y el calor extremo, y el impacto es la
  seguridad alimentaria.

Primera propuesta (descartada): “Con temperaturas cada vez más altas, ¿qué orden de cultivos evita
que un cultivo retrase la siembra del siguiente y le pegue al rendimiento?”
