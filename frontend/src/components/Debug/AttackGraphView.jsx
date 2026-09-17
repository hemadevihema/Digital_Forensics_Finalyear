import React, { useState, useEffect, useMemo, useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { fetchAttackGraph } from '../../services/api';

const NODE_WIDTH = 240;
const NODE_HEIGHT = 80;

function getLayoutedElements(nodes, edges, direction = 'TB') {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  const isHorizontal = direction === 'LR';

  dagreGraph.setGraph({
    rankdir: direction,
    ranksep: isHorizontal ? 90 : 70,
    nodesep: isHorizontal ? 50 : 50,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id) || { x: 0, y: 0 };
    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { layoutedNodes, layoutedEdges: edges };
}

// Custom Node Renderer with ReactFlow Handles
function ForensicNode({ data, selected, targetPosition = Position.Top, sourcePosition = Position.Bottom }) {
  const isMalicious = data.is_malicious;
  const isCritical = data.risk_level === 'CRITICAL';
  const nodeType = data.type || 'NODE';

  // Badge colors
  let typeColor = '#3b82f6';
  if (nodeType === 'USER' || nodeType === 'USER_PROMPT') typeColor = '#8b5cf6';
  else if (nodeType === 'DOCUMENT' || nodeType === 'CHUNK') typeColor = '#06b6d4';
  else if (nodeType === 'DETECTION') typeColor = isMalicious ? '#ef4444' : '#10b981';
  else if (nodeType === 'ATTRIBUTION') typeColor = isMalicious ? '#f59e0b' : '#10b981';
  else if (nodeType === 'OUTCOME') typeColor = isMalicious ? '#ef4444' : '#10b981';

  const borderColor = isCritical
    ? 'rgba(239, 68, 68, 0.9)'
    : isMalicious
    ? 'rgba(245, 158, 11, 0.8)'
    : selected
    ? '#6366f1'
    : 'rgba(255, 255, 255, 0.18)';

  const bgColor = isCritical
    ? 'rgba(45, 15, 20, 0.95)'
    : isMalicious
    ? 'rgba(45, 30, 15, 0.95)'
    : 'rgba(20, 24, 38, 0.95)';

  const boxShadow = isCritical
    ? '0 0 16px rgba(239, 68, 68, 0.5)'
    : isMalicious
    ? '0 0 14px rgba(245, 158, 11, 0.4)'
    : selected
    ? '0 0 14px rgba(99, 102, 241, 0.5)'
    : '0 4px 12px rgba(0, 0, 0, 0.35)';

  const handleColor = isCritical ? '#ef4444' : isMalicious ? '#f59e0b' : '#38bdf8';

  return (
    <div
      style={{
        position: 'relative',
        width: `${NODE_WIDTH}px`,
        padding: '10px 12px',
        borderRadius: '8px',
        background: bgColor,
        border: `1.5px solid ${borderColor}`,
        boxShadow,
        color: '#f3f4f6',
        fontSize: '11px',
        fontFamily: 'var(--font-sans, system-ui, sans-serif)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Target Handle: incoming flow lines */}
      <Handle
        type="target"
        position={targetPosition || Position.Top}
        style={{
          background: handleColor,
          width: 8,
          height: 8,
          borderRadius: '50%',
          border: '2px solid #0f172a',
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <span
          style={{
            fontSize: '9px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            color: typeColor,
            background: 'rgba(0,0,0,0.4)',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {nodeType}
        </span>
        {isMalicious && (
          <span
            style={{
              fontSize: '9px',
              fontWeight: 700,
              color: isCritical ? '#fca5a5' : '#fde68a',
              background: isCritical ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.3)',
              padding: '1px 5px',
              borderRadius: '4px',
            }}
          >
            {data.risk_level || 'THREAT'}
          </span>
        )}
      </div>
      <div
        style={{
          fontWeight: 600,
          fontSize: '11.5px',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          color: isCritical ? '#fee2e2' : '#ffffff',
        }}
        title={data.label}
      >
        {data.label}
      </div>

      {/* Source Handle: outgoing flow lines */}
      <Handle
        type="source"
        position={sourcePosition || Position.Bottom}
        style={{
          background: handleColor,
          width: 8,
          height: 8,
          borderRadius: '50%',
          border: '2px solid #0f172a',
        }}
      />
    </div>
  );
}

const nodeTypes = {
  forensicNode: ForensicNode,
};

export default function AttackGraphView({ requestId }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [layoutDirection, setLayoutDirection] = useState('TB'); // 'TB' | 'LR'

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!requestId) {
      setGraphData(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    setSelectedEdge(null);

    fetchAttackGraph(requestId)
      .then((data) => {
        if (!isMounted) return;
        setGraphData(data);

        // Convert API nodes to React Flow nodes
        const rfNodes = (data.nodes || []).map((n) => ({
          id: n.id,
          type: 'forensicNode',
          data: {
            ...n,
          },
          position: { x: 0, y: 0 },
        }));

        // Convert API edges to React Flow edges with distinct flow line styling
        const rfEdges = (data.edges || []).map((e) => {
          const isThreatEdge =
            e.relation === 'concludes' ||
            (e.label && (e.label.includes('POISONED') || e.label.includes('ATTRIBUTES')));
          const isDataFlow = e.relation === 'data_flow' || e.relation === 'invokes';
          const isOriginates = e.relation === 'originates';
          const isMerges = e.relation === 'merges';

          let strokeColor = '#94a3b8'; // Slate default
          if (isThreatEdge) strokeColor = '#ef4444'; // Bright Red
          else if (isDataFlow) strokeColor = '#38bdf8'; // Sky Blue
          else if (isOriginates) strokeColor = '#c084fc'; // Purple
          else if (isMerges) strokeColor = '#fbbf24'; // Amber

          return {
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.label,
            animated: isThreatEdge || isDataFlow,
            labelStyle: { fill: '#f1f5f9', fontSize: 10, fontWeight: 600 },
            labelBgStyle: { fill: '#0f172a', fillOpacity: 0.92, rx: 4, ry: 4 },
            labelBgPadding: [6, 3],
            style: {
              stroke: strokeColor,
              strokeWidth: isThreatEdge ? 2.5 : 2,
              strokeDasharray: isMerges ? '5 4' : undefined,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: strokeColor,
              width: 16,
              height: 16,
            },
            data: {
              label: e.label,
              relation: e.relation,
            },
          };
        });

        // Compute auto layout
        const { layoutedNodes, layoutedEdges } = getLayoutedElements(
          rfNodes,
          rfEdges,
          layoutDirection
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
      })
      .catch((err) => {
        if (isMounted) setError(err.message);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [requestId, layoutDirection]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node.data);
    setSelectedEdge(null);
  }, []);

  const onEdgeClick = useCallback((event, edge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  }, []);

  const toggleLayout = () => {
    const nextDir = layoutDirection === 'TB' ? 'LR' : 'TB';
    setLayoutDirection(nextDir);
  };

  if (!requestId) {
    return (
      <div className="debug-card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        Select a request from the dropdown above to render its causal Attack Graph.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="debug-card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        Reconstructing provenance execution path from stored MongoDB evidence...
      </div>
    );
  }

  if (error) {
    return (
      <div className="debug-card" style={{ padding: '1.5rem', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
        <h4 style={{ color: '#f87171', margin: '0 0 0.5rem 0' }}>Attack Graph Error</h4>
        <p style={{ color: '#fca5a5', fontSize: '0.9rem', margin: 0 }}>{error}</p>
      </div>
    );
  }

  const attribution = graphData?.source || 'NONE';
  const isMaliciousAttribution = attribution in { USER: 1, DOCUMENT: 1, BOTH: 1 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Top Status Bar */}
      <div
        className="glass-card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.75rem 1.25rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Request ID: </span>
            <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#fff' }}>
              {graphData?.request_id}
            </strong>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Attribution: </span>
            <span
              className={`forensic-badge ${
                attribution === 'USER' || attribution === 'BOTH'
                  ? 'badge-red'
                  : attribution === 'DOCUMENT'
                  ? 'badge-yellow'
                  : 'badge-green'
              }`}
            >
              {attribution}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Classification: </span>
            <span
              className={`forensic-badge ${
                graphData?.classification === 'MALICIOUS_INJECTION'
                  ? 'badge-red'
                  : graphData?.classification === 'SUSPICIOUS'
                  ? 'badge-yellow'
                  : 'badge-green'
              }`}
            >
              {graphData?.classification || 'BENIGN'}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Graph Stats: </span>
            <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
              {graphData?.total_nodes} nodes, {graphData?.total_edges} edges
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={toggleLayout}
            className="secondary-btn"
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
          >
            Layout: {layoutDirection === 'TB' ? 'Top-Down ↓' : 'Left-Right →'}
          </button>
        </div>
      </div>

      {/* Main Canvas & Inspection Drawer */}
      <div style={{ display: 'flex', gap: '1rem', height: '540px', position: 'relative' }}>
        {/* React Flow Container */}
        <div
          style={{
            flex: 1,
            height: '100%',
            borderRadius: '12px',
            overflow: 'hidden',
            border: '1px solid var(--border-subtle)',
            background: 'rgba(10, 12, 20, 0.85)',
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#334155" gap={20} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                if (n.data?.is_malicious) return '#ef4444';
                return '#475569';
              }}
              style={{ background: 'rgba(15, 23, 42, 0.85)' }}
            />
          </ReactFlow>
        </div>

        {/* Node & Edge Inspection Drawer */}
        <div
          className="glass-card"
          style={{
            width: '320px',
            height: '100%',
            overflowY: 'auto',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.85rem',
            background: 'rgba(17, 24, 39, 0.95)',
          }}
        >
          <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#e2e8f0', fontWeight: 600 }}>
            Inspector Details
          </h4>

          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8rem' }}>
              <div style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Node Type:</span>
                <div style={{ fontWeight: 700, color: '#60a5fa' }}>{selectedNode.type}</div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Label:</span>
                <div style={{ color: '#fff', fontWeight: 600 }}>{selectedNode.label}</div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Risk Assessment:</span>
                <div>
                  <span
                    className={`forensic-badge ${
                      selectedNode.is_malicious ? 'badge-red' : 'badge-green'
                    }`}
                  >
                    {selectedNode.is_malicious ? 'FLAGGED AS THREAT' : 'BENIGN'}
                  </span>
                  <span style={{ marginLeft: '0.5rem', color: '#94a3b8' }}>
                    Level: {selectedNode.risk_level}
                  </span>
                </div>
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Metadata Evidence:</span>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.5)',
                    padding: '0.6rem',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    color: '#cbd5e1',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </div>
            </div>
          ) : selectedEdge ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8rem' }}>
              <div style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Edge Relationship:</span>
                <div style={{ fontWeight: 700, color: '#a78bfa' }}>{selectedEdge.data?.label || selectedEdge.label}</div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Source Node:</span>
                <div style={{ color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                  {selectedEdge.source}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Target Node:</span>
                <div style={{ color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                  {selectedEdge.target}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Semantic Relation:</span>
                <div style={{ color: '#cbd5e1' }}>{selectedEdge.data?.relation || 'causal_link'}</div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic', marginTop: '1rem' }}>
              Click on any node or edge in the graph canvas to inspect its raw forensic properties and metadata.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
