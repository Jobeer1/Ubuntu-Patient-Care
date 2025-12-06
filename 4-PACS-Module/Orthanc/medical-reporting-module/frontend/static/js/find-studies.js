/* Find Studies - DICOM search and viewer integration */
(function() {
  const searchInput = document.getElementById('q');
  const searchBtn = document.getElementById('search');
  const resultsContainer = document.getElementById('results');
  const noteDiv = document.getElementById('note');
  
  let currentStudies = [];

  function showSpinner(show) {
    if (show) {
      resultsContainer.innerHTML = '<div class="text-gray-600">Searching...</div>';
    }
  }

  function showError(message) {
    resultsContainer.innerHTML = `<div class="text-red-600">Error: ${message}</div>`;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderStudies(studies) {
    if (!studies || studies.length === 0) {
      resultsContainer.innerHTML = '<div class="text-gray-600">No studies found.</div>';
      return;
    }

    const ul = document.createElement('ul');
    ul.className = 'space-y-3';

    studies.forEach((study, index) => {
      const li = document.createElement('li');
      li.className = 'p-4 border rounded hover:bg-gray-50 cursor-pointer';
      li.innerHTML = `
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="font-semibold text-lg">${escapeHtml(study.patientName || 'Unknown')}</div>
            <div class="text-sm text-gray-600">ID: ${escapeHtml(study.patientId || 'N/A')}</div>
            <div class="text-sm text-gray-600">${escapeHtml(study.studyDescription || 'No description')}</div>
            <div class="text-sm text-gray-600">${escapeHtml(study.modalitiesInStudy || 'Unknown modality')}</div>
          </div>
          <div class="text-right text-sm text-gray-500">
            <div>${escapeHtml(study.studyDate || 'Unknown date')}</div>
            <div>${study.seriesCount || 0} series</div>
            <div class="text-xs">${escapeHtml(study.accessionNumber || '')}</div>
          </div>
        </div>
      `;

      li.addEventListener('click', () => openStudy(study, index));
      ul.appendChild(li);
    });

    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(ul);
  }

  function openStudy(study, index) {
    // Show loading state
    const selectedItem = resultsContainer.children[0].children[index];
    if (selectedItem) {
      selectedItem.style.backgroundColor = '#e5f3ff';
    }

    // Load study metadata
    fetch(`/api/dicom/metadata/${study.studyInstanceUid}`, {
      credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showStudyViewer(data.study, data.series);
      } else {
        showError('Failed to load study details');
      }
    })
    .catch(error => {
      console.error('Study metadata error:', error);
      showError('Failed to load study details');
    });
  }

  function showStudyViewer(study, series) {
    // Create enhanced viewer modal with grid manager
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
    overlay.innerHTML = `
      <div class="bg-white rounded-lg max-w-7xl w-full max-h-screen overflow-auto m-4">
        <div class="p-4 border-b flex justify-between items-center">
          <div class="flex items-center gap-4">
            <div>
              <h2 class="text-xl font-bold">${escapeHtml(study.patientName)}</h2>
              <div class="text-sm text-gray-600">${escapeHtml(study.studyDescription)} • ${escapeHtml(study.studyDate)}</div>
            </div>
            
            <!-- Layout controls -->
            <div class="flex items-center gap-2 ml-8">
              <label class="text-sm font-medium">Layout:</label>
              <select id="layout-selector" class="border rounded px-2 py-1 text-sm">
                <option value="1x1">1×1</option>
                <option value="2x1">2×1</option>
                <option value="1x2">1×2</option>
                <option value="2x2" selected>2×2</option>
                <option value="3x2">3×2</option>
                <option value="2x3">2×3</option>
              </select>
              
              <button id="save-preset" class="px-3 py-1 bg-blue-600 text-white rounded text-sm">Save Preset</button>
              <select id="preset-selector" class="border rounded px-2 py-1 text-sm">
                <option value="">Load Preset...</option>
              </select>
            </div>
          </div>
          <button id="close-viewer" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        
        <div class="flex h-[80vh]">
          <!-- Series browser -->
          <div class="w-64 p-4 border-r bg-gray-50 overflow-y-auto">
            <h3 class="font-semibold mb-3">Series (${series.length})</h3>
            <div id="series-list" class="space-y-2"></div>
            
            <div class="mt-4 pt-4 border-t">
              <h4 class="font-medium text-sm mb-2">Instructions:</h4>
              <div class="text-xs text-gray-600">
                Drag series into viewer slots to compare images. 
                Use layout selector to change grid configuration.
              </div>
            </div>
          </div>
          
          <!-- Viewer grid -->
          <div class="flex-1 p-4">
            <div id="viewer-grid" class="grid gap-2 h-full">
              <!-- Grid slots will be generated here -->
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Initialize viewer state
    const viewerState = {
      currentLayout: '2x2',
      viewports: new Map(), // slotIndex -> { series, instanceIndex, element }
      series: series
    };

    // Close handlers
    document.getElementById('close-viewer').addEventListener('click', () => {
      document.body.removeChild(overlay);
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });

    // Layout manager
    const layoutSelector = document.getElementById('layout-selector');
    layoutSelector.addEventListener('change', (e) => {
      viewerState.currentLayout = e.target.value;
      updateViewerGrid(viewerState);
    });

    // Preset management
    loadPresets();
    document.getElementById('save-preset').addEventListener('click', () => saveCurrentPreset(viewerState));
    document.getElementById('preset-selector').addEventListener('change', (e) => {
      if (e.target.value) loadPreset(e.target.value, viewerState);
    });

    // Render draggable series list
    renderSeriesList(series, viewerState);
    
    // Initialize grid
    updateViewerGrid(viewerState);
  }

  function loadSeries(series, seriesIndex) {
    const viewerContainer = document.getElementById('viewer-container');
    const prevBtn = document.getElementById('prev-image');
    const nextBtn = document.getElementById('next-image');
    const counter = document.getElementById('image-counter');

    if (!series.instances || series.instances.length === 0) {
      viewerContainer.innerHTML = '<div class="text-gray-500">No instances in this series</div>';
      return;
    }

    let currentInstanceIndex = 0;
    
    function showInstance(index) {
      const instance = series.instances[index];
      if (!instance) return;

      viewerContainer.innerHTML = `
        <img src="${instance.wadoUrl}" 
             alt="DICOM Instance" 
             class="max-w-full max-h-full object-contain"
             onload="this.style.opacity=1" 
             onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OTk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+'
             style="opacity:0.5; transition: opacity 0.3s" />
      `;

      counter.textContent = `${index + 1} / ${series.instances.length}`;
      prevBtn.disabled = index === 0;
      nextBtn.disabled = index === series.instances.length - 1;
    }

    prevBtn.addEventListener('click', () => {
      if (currentInstanceIndex > 0) {
        currentInstanceIndex--;
        showInstance(currentInstanceIndex);
      }
    });

    nextBtn.addEventListener('click', () => {
      if (currentInstanceIndex < series.instances.length - 1) {
        currentInstanceIndex++;
        showInstance(currentInstanceIndex);
      }
    });

    prevBtn.disabled = false;
    nextBtn.disabled = false;

    // Load first instance
    showInstance(0);
  }

  function performSearch() {
    const query = searchInput.value.trim();
    
    showSpinner(true);

    fetch(`/api/dicom/qido?q=${encodeURIComponent(query)}&limit=20`, {
      credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        currentStudies = data.studies;
        renderStudies(currentStudies);
        
        if (currentStudies.length === 0) {
          noteDiv.textContent = 'No studies found. Try a different search term.';
        } else {
          noteDiv.textContent = `Found ${currentStudies.length} studies. Click a study to open viewer.`;
        }
      } else {
        showError(data.error || 'Search failed');
      }
    })
    .catch(error => {
      console.error('Search error:', error);
      showError('Search request failed');
    });
  }

  // Event listeners
  searchBtn.addEventListener('click', performSearch);
  
  // Helper function to render draggable series list
  function renderSeriesList(series, viewerState) {
    const seriesList = document.getElementById('series-list');
    series.forEach((s, index) => {
      const div = document.createElement('div');
      div.className = 'p-2 border rounded cursor-move hover:bg-white bg-gray-100';
      div.draggable = true;
      div.dataset.seriesIndex = index;
      div.innerHTML = `
        <div class="font-medium text-sm">${escapeHtml(s.seriesDescription || `Series ${s.seriesNumber}`)}</div>
        <div class="text-xs text-gray-600">${escapeHtml(s.modality)} • ${s.instanceCount} images</div>
        <div class="text-xs text-blue-600 mt-1">Drag to viewer slot</div>
      `;
      
      // Drag events
      div.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', index);
        div.classList.add('opacity-50');
      });
      
      div.addEventListener('dragend', (e) => {
        div.classList.remove('opacity-50');
      });
      
      seriesList.appendChild(div);
    });
  }

  // Grid layout configurations
  const GRID_LAYOUTS = {
    '1x1': { rows: 1, cols: 1, template: 'grid-cols-1 grid-rows-1' },
    '2x1': { rows: 1, cols: 2, template: 'grid-cols-2 grid-rows-1' },
    '1x2': { rows: 2, cols: 1, template: 'grid-cols-1 grid-rows-2' },
    '2x2': { rows: 2, cols: 2, template: 'grid-cols-2 grid-rows-2' },
    '3x2': { rows: 2, cols: 3, template: 'grid-cols-3 grid-rows-2' },
    '2x3': { rows: 3, cols: 2, template: 'grid-cols-2 grid-rows-3' }
  };

  // Update viewer grid layout
  function updateViewerGrid(viewerState) {
    const grid = document.getElementById('viewer-grid');
    const layout = GRID_LAYOUTS[viewerState.currentLayout];
    const totalSlots = layout.rows * layout.cols;
    
    // Store viewer state globally for button handlers
    window.currentViewerState = viewerState;
    
    // Clear existing grid classes and content
    grid.className = `grid gap-2 h-full ${layout.template}`;
    grid.innerHTML = '';
    
    // Create viewport slots
    for (let i = 0; i < totalSlots; i++) {
      const slot = document.createElement('div');
      slot.className = 'border-2 border-dashed border-gray-300 rounded flex items-center justify-center bg-gray-50 relative min-h-32';
      slot.dataset.slotIndex = i;
      
      // Check if this slot has a series loaded
      if (viewerState.viewports.has(i)) {
        const viewport = viewerState.viewports.get(i);
        renderViewportContent(slot, viewport, i, viewerState);
      } else {
        slot.innerHTML = `
          <div class="text-center text-gray-500">
            <div class="text-sm">Viewport ${i + 1}</div>
            <div class="text-xs mt-1">Drop series here</div>
          </div>
        `;
      }
      
      // Drop handlers
      slot.addEventListener('dragover', (e) => {
        e.preventDefault();
        slot.classList.add('border-blue-500', 'bg-blue-50');
      });
      
      slot.addEventListener('dragleave', (e) => {
        if (!slot.contains(e.relatedTarget)) {
          slot.classList.remove('border-blue-500', 'bg-blue-50');
        }
      });
      
      slot.addEventListener('drop', (e) => {
        e.preventDefault();
        slot.classList.remove('border-blue-500', 'bg-blue-50');
        
        const seriesIndex = parseInt(e.dataTransfer.getData('text/plain'));
        const series = viewerState.series[seriesIndex];
        
        if (series) {
          loadSeriesIntoViewport(series, i, viewerState);
        }
      });
      
      grid.appendChild(slot);
    }
  }

  // Render content in a viewport slot
  function renderViewportContent(slot, viewport, slotIndex, viewerState) {
    slot.className = 'border-2 border-gray-400 rounded bg-black relative overflow-hidden';
    slot.innerHTML = `
      <div class="absolute top-2 left-2 z-10 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
        ${escapeHtml(viewport.series.seriesDescription || `Series ${viewport.series.seriesNumber}`)} 
        (${viewport.instanceIndex + 1}/${viewport.series.instanceCount})
      </div>
      
      <div class="absolute top-2 right-2 z-10 flex gap-1">
        <button class="bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded" 
                onclick="clearViewport(${slotIndex})">×</button>
      </div>
      
      <div class="absolute bottom-2 left-2 right-2 z-10 flex gap-1">
        <button class="bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded flex-1" 
                onclick="previousImage(${slotIndex})" ${viewport.instanceIndex === 0 ? 'disabled' : ''}>←</button>
        <button class="bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded flex-1" 
                onclick="nextImage(${slotIndex})" ${viewport.instanceIndex >= viewport.series.instanceCount - 1 ? 'disabled' : ''}>→</button>
      </div>
      
      <img class="w-full h-full object-contain" 
           src="/api/dicom/wado?study=${encodeURIComponent(viewport.series.studyInstanceUID)}&series=${encodeURIComponent(viewport.series.seriesInstanceUID)}&instance=${viewport.instanceIndex}" 
           alt="DICOM Image" 
           onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzY5NzI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIE5vdCBBdmFpbGFibGU8L3RleHQ+PC9zdmc+'">
    `;
  }

  // Load series into specific viewport
  function loadSeriesIntoViewport(series, slotIndex, viewerState) {
    viewerState.viewports.set(slotIndex, {
      series: series,
      instanceIndex: 0,
      element: null
    });
    
    // Re-render just this slot
    const slot = document.querySelector(`[data-slot-index="${slotIndex}"]`);
    if (slot) {
      const viewport = viewerState.viewports.get(slotIndex);
      renderViewportContent(slot, viewport, slotIndex, viewerState);
    }
  }

  // Global functions for viewport controls (accessible from onclick)
  window.clearViewport = function(slotIndex) {
    if (window.currentViewerState) {
      window.currentViewerState.viewports.delete(slotIndex);
      updateViewerGrid(window.currentViewerState);
    }
  };

  window.previousImage = function(slotIndex) {
    if (window.currentViewerState && window.currentViewerState.viewports.has(slotIndex)) {
      const viewport = window.currentViewerState.viewports.get(slotIndex);
      if (viewport.instanceIndex > 0) {
        viewport.instanceIndex--;
        renderViewportContent(
          document.querySelector(`[data-slot-index="${slotIndex}"]`),
          viewport,
          slotIndex,
          window.currentViewerState
        );
      }
    }
  };

  window.nextImage = function(slotIndex) {
    if (window.currentViewerState && window.currentViewerState.viewports.has(slotIndex)) {
      const viewport = window.currentViewerState.viewports.get(slotIndex);
      if (viewport.instanceIndex < viewport.series.instanceCount - 1) {
        viewport.instanceIndex++;
        renderViewportContent(
          document.querySelector(`[data-slot-index="${slotIndex}"]`),
          viewport,
          slotIndex,
          window.currentViewerState
        );
      }
    }
  };

  // Layout presets management
  function loadPresets() {
    const selector = document.getElementById('preset-selector');
    const presets = JSON.parse(localStorage.getItem('dicom-viewer-presets') || '{}');
    
    // Clear existing options except first
    while (selector.children.length > 1) {
      selector.removeChild(selector.lastChild);
    }
    
    // Add saved presets
    Object.keys(presets).forEach(name => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      selector.appendChild(option);
    });
  }

  function saveCurrentPreset(viewerState) {
    const name = prompt('Enter preset name:');
    if (!name) return;
    
    const presets = JSON.parse(localStorage.getItem('dicom-viewer-presets') || '{}');
    presets[name] = {
      layout: viewerState.currentLayout,
      viewports: Array.from(viewerState.viewports.entries()).map(([slotIndex, viewport]) => ({
        slotIndex,
        seriesIndex: viewerState.series.findIndex(s => s.seriesInstanceUID === viewport.series.seriesInstanceUID),
        instanceIndex: viewport.instanceIndex
      }))
    };
    
    localStorage.setItem('dicom-viewer-presets', JSON.stringify(presets));
    loadPresets();
    alert(`Preset "${name}" saved!`);
  }

  function loadPreset(presetName, viewerState) {
    const presets = JSON.parse(localStorage.getItem('dicom-viewer-presets') || '{}');
    const preset = presets[presetName];
    
    if (!preset) return;
    
    // Update layout
    viewerState.currentLayout = preset.layout;
    document.getElementById('layout-selector').value = preset.layout;
    
    // Clear current viewports
    viewerState.viewports.clear();
    
    // Restore viewport assignments
    preset.viewports.forEach(({ slotIndex, seriesIndex, instanceIndex }) => {
      if (seriesIndex >= 0 && seriesIndex < viewerState.series.length) {
        viewerState.viewports.set(slotIndex, {
          series: viewerState.series[seriesIndex],
          instanceIndex: instanceIndex,
          element: null
        });
      }
    });
    
    // Re-render grid
    updateViewerGrid(viewerState);
    
    // Reset selector
    document.getElementById('preset-selector').value = '';
  }

  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      performSearch();
    }
  });

  // Initial demo search on load
  setTimeout(() => {
    searchInput.value = 'demo';
    performSearch();
  }, 500);

})();
