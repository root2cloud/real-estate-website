/** @odoo-module **/
console.log("Enhanced Property Map with Auto-Hide and Category Colors loaded ✅");

function initPropertyMap() {
    const dataEl = document.getElementById('property-data');
    const legendEl = document.getElementById('category-legend');
    if (!dataEl || !legendEl) {
        console.warn('Property map: required DOM elements not found');
        return;
    }

    // 1) Parse properties JSON safely
    let properties = [];
    try {
        const rawProps = dataEl.dataset.properties || '[]';
        properties = JSON.parse(rawProps);
        if (!Array.isArray(properties)) {
            console.error('Property data is not an array');
            properties = [];
        }
    } catch (e) {
        console.error('Invalid property JSON', e);
        properties = [];
    }

    // 2) Parse category colors safely
    let categoryColors = {};
    try {
        const rawColors = legendEl.dataset.colors || '{}';
        categoryColors = JSON.parse(rawColors);
    } catch (e) {
        console.error('Invalid category colors JSON', e);
        categoryColors = {};
    }

    console.log("Property map: loaded properties", properties.length);
    console.log("Property map: category colors", categoryColors);

    function initMap() {
        if (typeof L === 'undefined') {
            // wait for leaflet.js if it is still loading
            setTimeout(initMap, 200);
            return;
        }

        const el = document.getElementById('propertyMap');
        if (!el) {
            console.warn('Property map: #propertyMap not found');
            return;
        }

        const map = L.map(el);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(map);

        let openPopupMarker = null;
        let pointerInsidePopup = false;

        function createIcon(color) {
            return L.divIcon({
                className: 'custom-marker',
                html: `<div style="
                    width:32px;height:32px;border-radius:50%;
                    background:${color};border:3px solid white;
                    box-shadow:0 3px 12px rgba(0,0,0,0.3);
                    display:flex;align-items:center;justify-content:center;
                    font-size:14px;color:white;cursor:pointer;
                ">📍</div>`,
                iconSize: [32, 32],
                iconAnchor: [16, 16],
                popupAnchor: [0, -16],
            });
        }

        function popupHtml(p) {
            const img = p.image_url || '/web/static/img/placeholder.png';
            const price = p.price > 0
                ? `₹${Number(p.price).toLocaleString('en-IN')}`
                : 'Price on Request';
            return `
                <div class="property-hover-card">
                  <img src="${img}" class="property-image" onerror="this.src='/web/static/img/placeholder.png'"/>
                  <div class="property-content">
                    <h4 class="property-title">${p.name || ''}</h4>
                    <div class="property-category">${p.property_type || ''}</div>
                    <div class="property-location">📍 ${p.full_address || ''}</div>
                    <div class="property-price">${price}</div>
                    <div class="property-details">
                      ${p.plot_area ? `<div class="detail-item">📐 ${p.plot_area} sqft</div>` : ''}
                    </div>
                    <div class="action-buttons">
                      <a href="/property/${p.id}" class="btn-sm btn-primary">View Details</a>
                      ${p.contact_phone ? `<a href="tel:${p.contact_phone}" class="btn-sm btn-outline">📞 Call</a>` : ''}
                    </div>
                  </div>
                </div>`;
        }

        const markerLatLngs = [];

        // 3) Add markers
        properties.forEach((p) => {
            if (!p.latitude || !p.longitude) {
                return;
            }

            const color = categoryColors[p.property_type] || '#4f46e5';
            const marker = L.marker([p.latitude, p.longitude], {
                icon: createIcon(color),
            }).addTo(map);

            markerLatLngs.push([p.latitude, p.longitude]);

            marker.bindPopup(popupHtml(p), {
                closeButton: false,
                autoClose: false,
                closeOnClick: false,
                className: 'custom-popup',
                minWidth: 280,
                maxWidth: 320,
            });

            // Hover open/close logic
            marker.on('mouseover', function () {
                if (openPopupMarker && openPopupMarker !== marker) {
                    openPopupMarker.closePopup();
                }
                marker.openPopup();
                openPopupMarker = marker;
            });

            marker.on('mouseout', function () {
                setTimeout(() => {
                    if (openPopupMarker === marker && !pointerInsidePopup) {
                        marker.closePopup();
                        openPopupMarker = null;
                    }
                }, 100);
            });

            marker.on('popupopen', function (ev) {
                const popupObj = ev && ev.popup ? ev.popup : marker.getPopup();
                const popupEl = popupObj && popupObj.getElement ? popupObj.getElement() : null;
                if (!popupEl) {
                    return;
                }

                popupEl.addEventListener('mouseenter', () => {
                    pointerInsidePopup = true;
                });
                popupEl.addEventListener('mouseleave', () => {
                    pointerInsidePopup = false;
                    setTimeout(() => {
                        if (openPopupMarker === marker && !pointerInsidePopup) {
                            marker.closePopup();
                            openPopupMarker = null;
                        }
                    }, 100);
                });
            });
        });

        map.on('click', () => {
            if (openPopupMarker) {
                openPopupMarker.closePopup();
                openPopupMarker = null;
            }
        });

        // 4) Build legend
        legendEl.innerHTML = Object.entries(categoryColors)
            .map(
                ([cat, col]) => `
              <div class="legend-item">
                <div class="legend-color" style="background:${col}"></div>
                <span>${cat}</span>
              </div>`
            )
            .join('');

        // 5) Fit map to markers
        if (markerLatLngs.length === 1) {
            // Single property in current filter
            const only = markerLatLngs[0];
            map.setView(only, 15);
        } else if (markerLatLngs.length > 1) {
            // Multiple properties: fit to all
            const group = L.featureGroup(
                markerLatLngs.map((latlng) => L.marker(latlng))
            );
            const bounds = group.getBounds();

            if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.1));

                // Clamp if Leaflet zooms out too much
                if (map.getZoom() < 8) {
                    map.setView(bounds.getCenter(), 10);
                }
            } else {
                map.setView([20.5937, 78.9629], 5);
            }
        } else {
            // No properties in filter: default India view
            map.setView([20.5937, 78.9629], 5);
        }

        // 6) Ensure layout effects are applied
        setTimeout(() => {
            map.invalidateSize();
        }, 300);
    }

    initMap();
}

// Run immediately; script is loaded with `defer` so DOM is ready
initPropertyMap();
