/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


// For IE compatibility
if (!window.console) window.console = {};
if (!window.console.log) window.console.log = function () { };


// http://stackoverflow.com/a/21903119/881731
function GetUrlParameter(sParam) 
{
  var sPageURL = decodeURIComponent(window.location.search.substring(1));
  var sURLVariables = sPageURL.split('&');
  var sParameterName;
  var i;

  for (i = 0; i < sURLVariables.length; i++) 
  {
    sParameterName = sURLVariables[i].split('=');

    if (sParameterName[0] === sParam) 
    {
      return sParameterName[1] === undefined ? '' : sParameterName[1];
    }
  }

  return '';
};


function InitializePyramid(pyramid, tilesBaseUrl)
{
  $('#map').css('background', pyramid['BackgroundColor']);  // New in WSI 2.1

  var width = pyramid['TotalWidth'];
  var height = pyramid['TotalHeight'];
  var countLevels = pyramid['Resolutions'].length;

  var metersPerUnit = null;
  var imagedVolumeWidth = pyramid['ImagedVolumeWidth'];  // In millimeters
  var imagedVolumeHeight = pyramid['ImagedVolumeHeight'];
  if (imagedVolumeWidth !== undefined &&
      imagedVolumeHeight !== undefined) {
    metersPerUnit = parseFloat(imagedVolumeWidth) / (1000.0 * parseFloat(height));
    //metersPerUnit = parseFloat(imagedVolumeHeight) / (1000.0 * parseFloat(width));
  }

  // Maps always need a projection, but Zoomify layers are not geo-referenced, and
  // are only measured in pixels.  So, we create a fake projection that the map
  // can use to properly display the layer.
  var proj = new ol.proj.Projection({
    code: 'pixel',
    units: 'pixel',
    metersPerUnit: metersPerUnit,
    extent: [0, 0, width, height]
  });

  var extent = [0, -height, width, 0];

  // Disable the rotation of the map, and inertia while panning
  // http://stackoverflow.com/a/25682186
  var interactions = ol.interaction.defaults.defaults({
    //pinchRotate : false,
    dragPan: false  // disable kinetics
    //shiftDragZoom: false  // disable zoom box
  }).extend([
    new ol.interaction.DragPan(),
    new ol.interaction.DragRotate({
      //condition: ol.events.condition.shiftKeyOnly  // Rotate only when Shift key is pressed
    })
  ]);

  var controls = ol.control.defaults.defaults({
    attribution: false
  }).extend([
    new ol.control.ScaleLine({
      minWidth: 100
    })
  ]);


  var layer = new ol.layer.Tile({
    extent: extent,
    source: new ol.source.TileImage({
      projection: proj,
      tileUrlFunction: function(tileCoord, pixelRatio, projection) {
        return (tilesBaseUrl + (countLevels - 1 - tileCoord[0]) + '/' + tileCoord[1] + '/' + tileCoord[2]);
      },
      tileGrid: new ol.tilegrid.TileGrid({
        extent: extent,
        resolutions: pyramid['Resolutions'].reverse(),
        tileSizes: pyramid['TilesSizes'].reverse()
      })
    }),
    wrapX: false,
    projection: proj
  });


  var map = new ol.Map({
    target: 'map',
    layers: [ layer ],
    view: new ol.View({
      projection: proj,
      center: [width / 2, -height / 2],
      zoom: 0,
      minResolution: 0.1   // "1" means "do not interpelate over pixels"
    }),
    interactions: interactions,
    controls: controls
  });

  map.getView().fit(extent, map.getSize());
}


$(document).ready(function() {
  var seriesId = GetUrlParameter('series');
  var instanceId = GetUrlParameter('instance');

  if (seriesId.length != 0)
  {
    $.ajax({
      url : '../pyramids/' + seriesId,
      error: function() {
        alert('Error - Cannot get the pyramid structure of series: ' + seriesId);
      },
      success : function(pyramid) {
        InitializePyramid(pyramid, '../tiles/' + seriesId + '/');
      }
    });
  }
  else if (instanceId.length != 0)
  {
    var frameNumber = GetUrlParameter('frame');
    if (frameNumber.length == 0)
    {
      frameNumber = 0;
    }

    $.ajax({
      url : '../frames-pyramids/' + instanceId + '/' + frameNumber,
      error: function() {
        alert('Error - Cannot get the pyramid structure of frame ' + frameNumber + ' of instance: ' + instanceId);
      },
      success : function(pyramid) {
        InitializePyramid(pyramid, '../frames-tiles/' + instanceId + '/' + frameNumber + '/');
      }
    });
  }
  else
  {
    alert('Error - No series ID and no instance ID specified!');
  }
});
