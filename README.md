# Business Intelligence aplicado al análisis de participación de mercado del Cemento Antisalitre HS en CEMEX Perú

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
Durante los últimos 6 meses, la gerencia ha observado una disminución constante en la participación de mercado (market share) del Cemento Antisalitre HS.
A pesar de que la demanda de cemento a nivel nacional se mantiene en crecimiento y de la aplicación de promociones y beneficios económicos a sus asociados por la compra del producto mediante su programa de lealtad de puntos, el producto no mejora su participación frente a productos competidores y sustitutos. 
Mantener activa una promoción de triple de puntos implica un costo operativo y financiero, por lo que la empresa espera resultados positivos en los despachos del producto para poder compensar la inversión realizada.

### Objetivo
Por lo tanto, lo que se quiere responder es:
¿En qué zonas geográficas, canales de venta y periodos se concentra la caída de los despachos del Cemento Antisalitre HS, y cuál es el impacto real de la promoción de triple de puntos del programa de lealtad sobre el volumen despachado?

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

El Data Warehouse de operaciones logísticas y comerciales está diseñado bajo un modelo dimensional de tipo estrella. Este esquema permite analizar los despachos de materiales desde múltiples perspectivas geográficas, comerciales y temporales para evaluar estrategias comerciales. 

El modelo está compuesto por una tabla de hechos central, FACT_DESPACHOS, la cual se relaciona con once dimensiones para contextualizar el análisis operativo. A continuación, se detalla el diccionario de datos consolidado, ajustado a los datos reales de la operación.

## DIM_TIEMPO

La dimensión tiempo almacena la información temporal de los despachos.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_tiempo | INT | Identificador único de la dimensión (PK). |
| iddia | INT | Fecha de la operación en formato numérico YYYYMMDD (ej. 20241221). |
| anio | INT | Año correspondiente a la fecha del evento. |
| trimestre | INT | Trimestre del año asociado a la fecha. |
| mes | INT | Número del mes del evento. |
| semana | INT | Número de semana del año. |
| dia_semana | STRING | Día de la semana correspondiente a la fecha. |

## DIM_CLIENTE

Contiene los atributos descriptivos del cliente único que realiza la compra.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_cliente | INT | Identificador único de la dimensión (PK). |
| idcliente | INT | Identificador numérico de origen del cliente (ej. 56741). |
| tipo_cliente | STRING | Clasificación descriptiva del tipo de cliente. |
| segmento | STRING | Segmento comercial al que pertenece el cliente. |

## DIM_DESTINATARIO

Almacena la información del punto de entrega final de los productos.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_destinatario | INT | Identificador único de la dimensión (PK). |
| iddestinatario | INT | Identificador numérico de origen del punto final de entrega (ej. 22230). |
| cod_destinatario | STRING | Código alfanumérico del destinatario. |
| nombre_destinatario| STRING | Ciudad o dirección exacta del punto de entrega (ej. Trujillo, AV. AMERICAS). |

## DIM_PRODUCTO

Detalla el material comercial vendido.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_producto | INT | Identificador único de la dimensión (PK). |
| idmaterialcom | INT | Identificador numérico del material o producto (ej. 1612). |
| desmaterialcom | STRING | Descripción del material o producto comercial. |
| idunidadmedida | INT | Código numérico de la unidad de medida registrada original (ej. 1). |
| familia | STRING | Familia comercial a la que pertenece el producto. |
| linea | STRING | Línea de negocio del producto. |

## DIM_UNIDAD_MEDIDA

Dimensión para estandarizar la métrica de volumen de los materiales.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_unidad_medida | INT | Identificador único de la dimensión (PK). |
| idunidadmedida | INT | Código numérico de la unidad de medida (ej. 1). |
| desc_unidad | STRING | Descripción de la unidad (ej. bolsa, ton, m3). |

## DIM_OFICINA

Agrupa las operaciones logísticas según la sucursal o establecimiento responsable de gestionar el despacho.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_oficina | INT | Identificador único de la dimensión (PK). |
| idoficina | INT | Identificador numérico de origen de la oficina o sucursal comercial (ej. 1212). |
| nombre_oficina | STRING | Nombre descriptivo de la oficina. |
| zona | STRING | Zona geográfica operativa de la oficina. |

## DIM_RUTA

Describe las rutas logísticas de reparto, vital para identificar las zonas geográficas donde se concentran los despachos.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_ruta | INT | Identificador único de la dimensión (PK). |
| idruta | INT | Identificador numérico de la ruta de reparto asociada a la oficina (ej. 235). |
| descripcion_ruta | STRING | Descripción textual de la ruta de distribución. |
| zona_destino | STRING | Clasificación de la zona de destino de la ruta. |

## DIM_TRANSPORTE

Contiene la información de la empresa, los vehículos y el personal asignado al despacho.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_transporte | INT | Identificador único de la dimensión (PK). |
| idempresatransporte| INT | Identificador de origen de la empresa transportista. |
| nombre_empresa | STRING | Razón social o nombre de la empresa de transporte. |
| idtipovehiculo | INT | Código numérico del tipo de vehículo utilizado (ej. 7). |
| placa | STRING | Placa alfanumérica del vehículo asignado al despacho (ej. C8N705). |
| chofer | STRING | Nombre del chofer asignado a la entrega (ej. HUGO CESAR). |
| brevete | STRING | Número de licencia de conducir o brevete del chofer (ej. D4124927). |

## DIM_VENDEDOR

Agrupa los datos del personal o sucursal comercial que gestiona la venta.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_vendedor | INT | Identificador único de la dimensión (PK). |
| codvendedorinterno | INT | Código numérico del vendedor responsable de la venta. |
| vendedorinterno | STRING | Nombre o descripción de la sucursal o vendedor (ej. DINO Sucursal). |
| idgrupovendedor | INT | Identificador del grupo comercial al que pertenece. |

## DIM_CANAL

Permite segmentar las operaciones por el medio o tipo de socio de negocio.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_canal | INT | Identificador único de la dimensión (PK). |
| idsubcanal | INT | Identificador numérico de origen del canal de venta (ej. 3). |
| desc_canal | STRING | Descripción del canal. |

## DIM_TIPO_DESPACHO

Clasifica los atributos que describen el estado logístico y el tipo de operación realizada.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_tipo_despacho | INT | Identificador único de la dimensión (PK). |
| idtipodespacho | INT | Código numérico del tipo de despacho originado (ej. 7). |
| idclasedespacho | INT | Código numérico de la clase específica de despacho. |
| idestadoentrega | INT | Código numérico del estado actual de la entrega (ej. 1). |
| estadoalmacen | STRING | Código o estado operativo en almacén (ej. 1). |

## FACT_DESPACHOS

Tabla central que consolida las métricas cuantitativas y transaccionales del negocio. Cruza los volúmenes, montos e información de facturación.

| Nombre de columna | Tipo de dato | Descripción |
| :--- | :--- | :--- |
| id_despacho | INT | Identificador único del registro de despacho (PK). |
| Llaves Foraneas | INT | FKs: id_tiempo, id_cliente, id_destinatario, id_producto, id_oficina, id_ruta, id_transporte, id_vendedor, id_canal, id_tipo_despacho, id_unidad_medida. |
| nroentrega | STRING | Número único de la entrega (ej. 2301740686). |
| nropedido | STRING | Dimensión degenerada: Número de pedido asociado (ej. 401471029). |
| nrofactura | STRING | Dimensión degenerada: Número de documento o comprobante tributario. |
| nroguiaremision | STRING | Dimensión degenerada: Número alfanumérico de guía de remisión (ej. GR-T155). |
| ctdpedida | DECIMAL | Medida: Cantidad solicitada por el cliente (ej. 21.25). |
| ctddespachada | DECIMAL | Medida: Cantidad efectivamente despachada (ej. 21.25). |
| vtadespachada | DECIMAL | Medida: Venta neta del despacho (ej. 12627.26). |
| vtadespachadabruto| DECIMAL | Medida: Venta bruta antes de aplicar cualquier descuento. |
| descuento | DECIMAL | Medida: Monto total de descuento o promoción aplicado. |
| importefletefactura| DECIMAL | Medida: Costo del flete logístico asociado a la entrega. |
## 5. Modelo multidimensional
<img width="1600" height="1310" alt="WhatsApp Image 2026-09-25 at 3 19 04 PM" src="https://github.com/user-attachments/assets/45389707-20a3-4f47-acbc-68ffd625fde1" />



## 6. Dataset
https://drive.google.com/drive/folders/1pt_AFsa8XqcQDsAzD5DGkNqI7F3tiFYS?usp=sharing 

## 7. Referencias
Chaudhuri, S., & Dayal, U. (1997). An overview of data warehousing and OLAP technology. ACM SIGMOD Record, 26(1), 65–74. https://doi.org/10.1145/248603.248616

Codd, E. F., Codd, S. B., & Salley, C. T. (1993). Providing OLAP (On-line analytical processing) to user-analysts: An IT mandate. E.F. Codd & Associates. https://staff.icar.cnr.it/manco/Teaching/2006/datamining/articoli/olapcoddwp.pdf

Gartner. (s.f.). Business intelligence (BI) [Entrada de glosario]. Gartner Glossary. https://www.gartner.com/en/information-technology/glossary/business-intelligence-bi

Inmon, W. H. (1992). Building the data warehouse. Wiley.

Kimball, R., & Ross, M. (2013). The data warehouse toolkit: The definitive guide to dimensional modeling (3.ª ed.). Wiley.

