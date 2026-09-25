# Proyecto CEMEX Peru

## Integrantes:
* Carlos Mariños
* Andrea Nepo
* Paula Ramos
* Daniela Yaulli

## 1. Introducción a la empresa
CEMEX nació en 1906 en Nuevo León, México, como una pequeña planta regional llamada Cementos Hidalgo. En 1931, se fusionó con Cementos Portland Monterrey, dando origen oficial a Cementos Mexicanos (CEMEX).
Las operaciones de CEMEX en Peru se dan principalmente bajo un modelo de importación y distribución, consolidándose como un fuerte competidor en el mercado nacional de materiales desde su ingreso en 2007.
CEMEX ofrece una cartera diversificada de materiales para la construcción y centra su estrategia global en la sostenibilidad, la digitalización y la economía circular. 


## 2. Problemática
Durante los últimos 6 meses, se ha observado una disminución constante en la participación de mercado (market share) del Cemento Antisalitre HS.
A pesar de que la demanda de cemento a nivel nacional se mantiene en crecimiento y de la aplicación de promociones y beneficios económicos a sus asociados por la compra del producto mediante su programa de lealtad de puntos, el producto no mejora su participación frente a productos competidores y sustitutos.
Mantener activa una promoción de triple de puntos implica un costo operativo y financiero, por lo que la empresa espera resultados positivos en los despachos del producto para poder compensar la inversión realizada.

## 3. Marco teórico
### Business Intelligence
El término Business Intelligence [BI] fue usado por primera por vez Hans Peter Luhn en 1958, pero pasó a tener reconocimiento recién en los años 90s gracias a Gartner, quien lo define como un proceso que usa tecnología para analizar datos y presentar información útil, con el fin de que ejecutivos y gerentes tomen mejores decisiones de negocio.
Para el caso de este proyecto, dirigido a CEMEX, BI sirve para convertir los datos de los despachos de cemento (pedidos, entregas, facturación) en información que ayude a tomar decisiones comerciales. Por ejemplo, saber si la promoción de "triple puntos" del producto Antisalitre HS realmente está funcionando o si solo está generando gasto sin mejorar la participación de mercado.

### Data Warehouse y Datamart
El Data Warehouse [DW] es el repositorio central que reúne datos extraídos de los sistemas operacionales, los cuales son transformados para hacerlos consistentes y cargados para su análisis (Inmon, 1992). Por su parte, el Datamart, es un subconjunto del DW enfocado en un área específica del negocio, como por ejemplo, ventas, marketing o recursos humanos, es más rápido de construir, más económico y más fácil de mantener que un DW completo.

### Modelamiento Dimensional (Data Dimensional)
Este modelo fue desarrollado por Ralph Kimball, es el estándar para diseñar la capa analítica de un data warehouse. Se basa en organizar los datos en dos tipos de tablas: tablas de hechos (que guardan las medidas) y tablas de dimensiones (que dan el contexto descriptivo). (Kimball y Ross, 2013)
Tabla de hechos. Guarda las medidas o métricas de un evento del negocio (normalmente números) además de las llaves foráneas que apuntan a las dimensiones.
Tabla de dimensiones. Guarda los atributos descriptivos (algunos ejemplos pueden ser: cliente, producto, ruta, transporte, tiempo) que sirven para filtrar y agrupar las medidas de la tabla de hechos.
Esquema estrella vs. copo de nieve. En un esquema estrella, la tabla de hechos se conecta directo con tablas de dimensión que no están normalizadas. De acuerdo a Kimball (2013) se recomienda evitar normalizar las dimensiones (el "copo de nieve") salvo que sea realmente necesario, porque hace las consultas más lentas y complica el modelo para el usuario final.

### Cubos OLAP
El término OLAP (Online Analytical Processing) fue desarrollado por Codd, Codd y Salley en 1993, quienes plantean un tipo de procesamiento de datos distinto al transaccional, pensado específicamente para el análisis. Luego, Chaudhuri y Dayal (1997), explican que un cubo OLAP se construye típicamente sobre un esquema estrella o copo de nieve dentro de un data warehouse: las medidas salen de la tabla de hechos y las dimensiones de las tablas de dimensión. Para CEMEX, esto significará poder ver, por ejemplo, la venta despachada de Antisalitre HS por ruta, por vendedor y por mes, para saber si la promoción de puntos realmente está dando resultado.



## 4. Diccionario de datos
<img width="583" height="654" alt="image" src="https://github.com/user-attachments/assets/dd05f81e-2fce-4597-9e28-23c0fe1b50a2" />


## 5. Modelo multidimensional

## 6. Dataset
https://drive.google.com/drive/folders/1pt_AFsa8XqcQDsAzD5DGkNqI7F3tiFYS?usp=sharing 

## 7. Referencias
Chaudhuri, S., & Dayal, U. (1997). An overview of data warehousing and OLAP technology. ACM SIGMOD Record, 26(1), 65–74. https://doi.org/10.1145/248603.248616

Codd, E. F., Codd, S. B., & Salley, C. T. (1993). Providing OLAP (On-line analytical processing) to user-analysts: An IT mandate. E.F. Codd & Associates. https://staff.icar.cnr.it/manco/Teaching/2006/datamining/articoli/olapcoddwp.pdf

Gartner. (s.f.). Business intelligence (BI) [Entrada de glosario]. Gartner Glossary. https://www.gartner.com/en/information-technology/glossary/business-intelligence-bi

Inmon, W. H. (1992). Building the data warehouse. Wiley.

Kimball, R., & Ross, M. (2013). The data warehouse toolkit: The definitive guide to dimensional modeling (3.ª ed.). Wiley.

