import geopandas as gpd

lida2 = gpd.read_file('ruta a fichero lida2.shp')

for row, cuadricula in lida2.iterrows():
  url = 'https://centrodedescargas.cnig.es/CentroDescargas/descargaDir'
  with requests.post( url, data={'secuencialDescDir': product['id']}, stream=True ) as r:
    with open(product['nombre'], 'wb') as f:
        f.write(r.content)
