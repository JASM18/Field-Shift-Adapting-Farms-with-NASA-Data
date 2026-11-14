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

## Pregunta de investigación (en discusión)

Propuesta del equipo:

> “Con temperaturas cada vez más altas, ¿qué orden de cultivos evita que un cultivo retrase la
> siembra del siguiente y le pegue al rendimiento?”
