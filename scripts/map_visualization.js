import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

const MapVisualization = () => {
  const [selectedMap, setSelectedMap] = useState('lorencia');

  const maps = {
    lorencia: {
      spawns: [
        { x: 137, y: 137, label: 'Top-Left' },
        { x: 153, y: 118, label: 'Bottom-Right' },
        { x: 153, y: 137, label: 'Top-Right' },
        { x: 133, y: 118, label: 'Bottom-Left' }
      ],
      gates: [
        { x: 132, y: 149, label: 'Top Gate Start' },
        { x: 135, y: 149, label: 'Top Gate End' },
        { x: 183, y: 56, label: 'Left Gate Start' },
        { x: 183, y: 59, label: 'Left Gate End' }
      ],
      monsterSpots: [
        { x: 128, y: 200, label: 'Tarkan Monster Spot' }
      ]
    },
    tarkan: {
      spawns: [
        { x: 189, y: 72, label: 'Top-Left' },
        { x: 205, y: 54, label: 'Bottom-Right' },
        { x: 205, y: 72, label: 'Top-Right' },
        { x: 189, y: 54, label: 'Bottom-Left' }
      ],
      monsterSpots: [
        { x: 123, y: 91, label: 'Monster Spot' }
      ]
    }
  };

  const scaleCoord = (coord, type) => {
    const scale = type === 'x' ? 2 : -2;
    const offset = type === 'x' ? 0 : 400;
    return type === 'x' ? coord * scale : offset + coord * scale;
  };

  const renderPoint = (point, color, size = 4) => (
    <g key={`${point.x}-${point.y}-${point.label}`}>
      <circle 
        cx={scaleCoord(point.x, 'x')} 
        cy={scaleCoord(point.y, 'y')} 
        r={size} 
        fill={color}
      />
      <text 
        x={scaleCoord(point.x, 'x') + 10} 
        y={scaleCoord(point.y, 'y')} 
        fontSize="12" 
        fill="white"
      >
        {point.label} ({point.x}, {point.y})
      </text>
    </g>
  );

  const renderPath = (start, end, color) => (
    <line
      x1={scaleCoord(start.x, 'x')}
      y1={scaleCoord(start.y, 'y')}
      x2={scaleCoord(end.x, 'x')}
      y2={scaleCoord(end.y, 'y')}
      stroke={color}
      strokeWidth="2"
      strokeDasharray="4"
    />
  );

  return (
    <Card className="w-full max-w-4xl bg-gray-900">
      <CardHeader>
        <CardTitle className="text-white">
          MU Online Map Movement Guide - {selectedMap.charAt(0).toUpperCase() + selectedMap.slice(1)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          <select 
            value={selectedMap}
            onChange={(e) => setSelectedMap(e.target.value)}
            className="bg-gray-800 text-white p-2 rounded"
          >
            <option value="lorencia">Lorencia</option>
            <option value="tarkan">Tarkan</option>
          </select>
        </div>
        
        <svg viewBox="0 0 800 400" className="w-full h-96 bg-gray-800">
          {/* Grid lines */}
          {[...Array(20)].map((_, i) => (
            <g key={`grid-${i}`}>
              <line 
                x1={i * 40} y1="0" 
                x2={i * 40} y2="400" 
                stroke="#333" 
                strokeWidth="1"
              />
              <line 
                x1="0" y1={i * 20} 
                x2="800" y2={i * 20} 
                stroke="#333" 
                strokeWidth="1"
              />
            </g>
          ))}
          
          {/* Map elements */}
          {maps[selectedMap].spawns.map(point => renderPoint(point, '#ff6b6b', 6))}
          {maps[selectedMap].gates && maps[selectedMap].gates.map(point => renderPoint(point, '#4ecdc4', 4))}
          {maps[selectedMap].monsterSpots.map(point => renderPoint(point, '#ffd93d', 5))}
          
          {/* Movement paths */}
          {selectedMap === 'lorencia' && (
            <>
              {renderPath(maps.lorencia.spawns[0], maps.lorencia.gates[0], '#6c5ce7')}
              <text x="20" y="30" fill="#ff6b6b" fontSize="12">● Spawn Points</text>
              <text x="20" y="50" fill="#4ecdc4" fontSize="12">● Gates</text>
              <text x="20" y="70" fill="#ffd93d" fontSize="12">● Monster Spots</text>
            </>
          )}
        </svg>
      </CardContent>
    </Card>
  );
};

export default MapVisualization;