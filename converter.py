import pdal
import json
from osgeo import gdal, osr
import numpy as np
import laspy
from os import path

class FuelMap():
    def __init__( self, fichero ):
        self.fichero = path.join('las', fichero)
        with laspy.open( self.fichero ) as f:
            x_min = round(f.header.x_min)
            x_max = round(f.header.x_max)
            y_min = round(f.header.y_min)
            y_max = round(f.header.y_max)
            self.originX = f.header.x_min
            self.originY = f.header.y_max
            self.bounds = ([x_min, x_max], [y_min, y_max])
            self.extensionX = x_max - x_min
            self.extensionY = y_max - y_min
            self.pixelsX = int( self.extensionX / 25 )
            self.pixelsY = int( self.extensionY / 25 )
            print(self.bounds, self.extensionY, self.pixelsY)
            print(self.bounds, self.extensionX, self.pixelsX)
            self.lat = int(y_max / 1000)
            self.lng = int(x_min / 1000)

    def getPipeline( self, tipo ):
        tipos = {
                    'edificaciones': {
                        'class': '[6:6]',
                        'height': '[0.1:60]',
                        'filename': 'edificaciones_{}_{}.tif'.format( self.lng, self.lat ),
                        },

                    'matorral': {
                        'class': '[3:5]',
                        'height': '[0.2:4]',
                        'filename': 'matorral_{}_{}.tif'.format( self.lng, self.lat ),
                        },
                    'arbolado': {
                        'class': '[3:5]',
                        'height': '[4:50]',
                        'filename': 'arbolado_{}_{}.tif'.format( self.lng, self.lat ),
                        }
                }

        return [
                self.fichero,
                {
                    'type': 'filters.hag_nn',
                    },
                {
                    'type': 'filters.range',
                    'limits': 'HeightAboveGround{}, Classification{}'.format( tipos[tipo]['height'],tipos[tipo]['class'] )
                    },
                {
                    'type': 'writers.gdal',
                    'filename': tipos[tipo]['filename'],
                    'resolution': '2.5',
                    'dimension': 'HeightAboveGround',
                    'output_type': 'max',
                    'bounds': str(self.bounds)
                    }
                ]

    def createHeightMap( self, tipo ):
        p = self.getPipeline( tipo )
        b = json.dumps(p)
        pipeline = pdal.Pipeline(b)
        count = pipeline.execute()

    def createFuelMap( self ):
        ds_arb = gdal.Open( 'arbolado_{}_{}.tif'.format( self.lng, self.lat ) )
        array_arb = np.array(ds_arb.ReadAsArray())

        ds_mat = gdal.Open( 'matorral_{}_{}.tif'.format( self.lng, self.lat ) )
        array_mat = np.array(ds_mat.ReadAsArray())

        ds_edif = gdal.Open( 'edificaciones_{}_{}.tif'.format( self.lng, self.lat ) )
        array_edif = np.array(ds_edif.ReadAsArray())

        new_array = np.zeros([self.pixelsY, self.pixelsX])

        for new_col in range(new_array.shape[0]):
            for new_row in range(new_array.shape[1]):
                print(new_col)
                print(new_row)
                arb = np.full(100, np.nan)
                mat = np.full(100, np.nan)
                amb = np.full(100, np.nan)
                edif = np.full(100, np.nan)
                coef_arb = 0
                coef_amb = 0
                coef_mat = 0
                coef_edif = 0
                for col in range(10):
                    for row in range(10):
                        data_arb = array_arb[new_col * 10 + col][new_row * 10 + row]
                        data_mat = array_mat[new_col * 10 + col][new_row * 10 + row]
                        data_edif = array_edif[new_col * 10 + col][new_row * 10 + row]
                        if data_edif != -9999:
                            coef_edif += 1
                        if data_arb != -9999 and data_mat != -9999:
                            amb[col * 10 + row] = data_arb
                            coef_amb += 1
                        if data_mat != -9999 and data_arb == -9999:
                            mat[col * 10 + row] = data_mat
                            coef_mat += 1
                        if data_arb != -9999 and data_mat == -9999:
                            arb[col * 10 + row] = data_arb
                            coef_arb += 1

                if coef_edif > 80:
                    new_array[new_col, new_row] = 0

                elif coef_arb + coef_mat + coef_amb > 66:
                    if coef_arb >= coef_amb and coef_arb >= coef_mat:
        #                 pto = getCoordinates(new_col, new_row)
        #                 sp1 = consulta(pto)
        #                 if sp1 == 21:
        #                     new_array[new_col, new_row] = 8
        #                 else:
        #                     new_array[new_col, new_row] = 9
                        new_array[new_col, new_row] = 8
                    elif coef_mat >= coef_amb and coef_mat >= coef_arb:
                        if np.nanmean(mat) < 0.8:
                            new_array[new_col, new_row] = 5
                        elif np.nanmean(mat) < 1.6:
                            new_array[new_col, new_row] = 6
                        else:
                            new_array[new_col, new_row] = 4
                    else:
                        new_array[new_col, new_row] = 7
                else:
        #             pto = getCoordinates(new_col, new_row)
        #             clas = consulta2(pto)
        #                 if clas == 300:
        #                     new_array[new_col, new_row] = 0
        #                 else:
        #                     if coef_mat + coef_arb + coef_amb < 33:
        #                         new_array[new_col, new_row] = 1
        #                     else:
        #                         new_array[new_col, new_row] = 2
                            if coef_mat + coef_arb + coef_amb < 33:
                                new_array[new_col, new_row] = 1
                            else:
                                new_array[new_col, new_row] = 2

        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create('fm_{}_{}.tif'.format( self.lng, self.lat ), self.pixelsX, self.pixelsY, 1, gdal.GDT_Byte)
        outRaster.SetGeoTransform((self.originX, 25, 0, self.originY, 0, -25))
        outRaster.GetRasterBand(1).WriteArray(new_array)
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromEPSG(25830)
        outRaster.SetProjection(outRasterSRS.ExportToWkt())
        outRaster.FlushCache()
