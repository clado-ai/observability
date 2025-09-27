"""
Enhanced DOM Utility

Handles DOM snapshot capture functionality using CDP DOMSnapshot with enhanced processing
for visibility, clickability, cursor styles, and other layout information.
"""

import logging
from typing import Any, Dict, Optional, List

from .base_client import BaseCDPClient

SnapshotLookup = Dict[int, Any]
RawSnapshot = Dict[str, Any]


logger = logging.getLogger(__name__)

REQUIRED_COMPUTED_STYLES = [
    "display",
    "visibility",
    "opacity",
    "overflow",
    "overflow-x",
    "overflow-y",
    "cursor",
    "pointer-events",
    "position",
    "background-color",
]


class DOMUtil:
    """
    Utility for capturing DOM snapshots and structure data.
    """

    def __init__(self, client: BaseCDPClient) -> None:
        self.client = client

    async def capture_snapshot(
        self,
        session_id: Optional[str] = None,
    ) -> SnapshotLookup:
        """
        Capture a DOM snapshot and return the enhanced optimized result.

        Args:
            session_id: Optional session ID for targeted snapshot

        Returns:
            Dictionary mapping snapshot index to enhanced node data
        """
        try:
            params: Dict[str, Any] = {
                "computedStyles": REQUIRED_COMPUTED_STYLES,
                "includeEventListeners": True,
            }

            fut = await self.client.send(
                "DOMSnapshot.captureSnapshot",
                params=params,
                expect_result=True,
                session_id=session_id,
            )
            assert fut is not None
            msg = await fut  # type: ignore
            raw_snapshot = msg.get("result", {})

            enhanced_snapshot = self.build_enhanced_snapshot_lookup(raw_snapshot)
            return enhanced_snapshot
        except Exception as e:
            logger.error(f"Failed to capture DOM snapshot: {e}")
            return {}

    async def capture_snapshot_from_all_pages(
        self,
    ) -> Dict[str, SnapshotLookup]:
        """
        Capture DOM snapshots from all attached page sessions.

        Args:

        Returns:
            Dictionary mapping target_id to enhanced snapshot lookup
        """
        snapshots = {}
        for target_id, session_id in self.client.get_session_ids().items():
            snapshot_data = await self.capture_snapshot(
                session_id=session_id,
            )
            snapshots[target_id] = snapshot_data
        return snapshots

    def _parse_rare_boolean_data(self, rare_data: Dict[str, Any], index: int) -> Optional[bool]:
        """Parse rare boolean data from snapshot - returns True if index is in the rare data."""
        if not rare_data or "index" not in rare_data:
            return None
        return index in rare_data["index"]

    def _parse_computed_styles(
        self, strings: List[str], style_indices: List[int]
    ) -> Dict[str, str]:
        """Parse computed styles from layout tree using string indices."""
        styles = {}
        for i, style_index in enumerate(style_indices):
            if i < len(REQUIRED_COMPUTED_STYLES) and 0 <= style_index < len(strings):
                styles[REQUIRED_COMPUTED_STYLES[i]] = strings[style_index]
        return styles

    def build_enhanced_snapshot_lookup(
        self,
        snapshot: RawSnapshot,
    ) -> SnapshotLookup:
        """
        Build a lookup table of backend node ID to enhanced snapshot data.

        Args:
            snapshot: Raw DOM snapshot data from CDP

        Returns:
            Dictionary mapping snapshot index to enhanced node data
        """
        snapshot_lookup: SnapshotLookup = {}

        if not snapshot.get("documents"):
            return snapshot_lookup

        strings = snapshot.get("strings", [])

        for document in snapshot["documents"]:
            nodes = document.get("nodes", {})
            layout = document.get("layout", {})

            layout_index_map = {}
            if layout and "nodeIndex" in layout:
                for layout_idx, node_index in enumerate(layout["nodeIndex"]):
                    if node_index not in layout_index_map:
                        layout_index_map[node_index] = layout_idx

            node_count = 0
            if "nodeType" in nodes:
                node_count = len(nodes["nodeType"])
            elif "nodeName" in nodes:
                node_count = len(nodes["nodeName"])
            else:
                for key in nodes:
                    if isinstance(nodes[key], list):
                        node_count = len(nodes[key])
                        break

            for snapshot_index in range(node_count):
                node_type = None
                node_name = None
                node_value = None
                attributes = None
                backend_node_id = None

                if "nodeType" in nodes and snapshot_index < len(nodes["nodeType"]):
                    node_type = nodes["nodeType"][snapshot_index]
                if "nodeName" in nodes and snapshot_index < len(nodes["nodeName"]):
                    node_name = (
                        strings[nodes["nodeName"][snapshot_index]]
                        if nodes["nodeName"][snapshot_index] < len(strings)
                        else None
                    )
                if "nodeValue" in nodes and snapshot_index < len(nodes["nodeValue"]):
                    node_value = (
                        strings[nodes["nodeValue"][snapshot_index]]
                        if nodes["nodeValue"][snapshot_index] < len(strings)
                        else None
                    )
                if "attributes" in nodes and snapshot_index < len(nodes["attributes"]):
                    attr_indices = nodes["attributes"][snapshot_index]
                    if attr_indices:
                        attributes = {}
                        for i in range(0, len(attr_indices), 2):
                            if i + 1 < len(attr_indices):
                                attr_name_idx = attr_indices[i]
                                attr_value_idx = attr_indices[i + 1]
                                if attr_name_idx < len(strings) and attr_value_idx < len(strings):
                                    attr_name = strings[attr_name_idx]
                                    attr_value = strings[attr_value_idx]
                                    attributes[attr_name] = attr_value
                if "backendNodeId" in nodes and snapshot_index < len(nodes["backendNodeId"]):
                    backend_node_id = nodes["backendNodeId"][snapshot_index]

                is_clickable = None
                if "isClickable" in nodes:
                    is_clickable = self._parse_rare_boolean_data(
                        nodes["isClickable"], snapshot_index
                    )

                enhanced_data = {
                    "node_type": node_type,
                    "node_name": node_name,
                    "node_value": node_value,
                    "attributes": attributes,
                    "backend_node_id": backend_node_id,
                    "is_clickable": is_clickable,
                    "cursor_style": None,
                    "bounding_box": None,
                    "computed_styles": {},
                    "client_rects": None,
                    "scroll_rects": None,
                    "paint_order": None,
                    "stacking_contexts": None,
                }

                if snapshot_index in layout_index_map:
                    layout_idx = layout_index_map[snapshot_index]

                    bounds = layout.get("bounds", [])
                    if layout_idx < len(bounds):
                        bounds_data = bounds[layout_idx]
                        if len(bounds_data) >= 4:
                            raw_x, raw_y, raw_width, raw_height = (
                                bounds_data[0],
                                bounds_data[1],
                                bounds_data[2],
                                bounds_data[3],
                            )
                            enhanced_data["bounding_box"] = {
                                "x": raw_x,
                                "y": raw_y,
                                "width": raw_width,
                                "height": raw_height,
                            }

                    styles = layout.get("styles", [])
                    if layout_idx < len(styles):
                        style_indices = styles[layout_idx]
                        computed_styles = self._parse_computed_styles(strings, style_indices)
                        enhanced_data["computed_styles"] = computed_styles
                        enhanced_data["cursor_style"] = computed_styles.get("cursor")

                    paint_orders = layout.get("paintOrders", [])
                    if layout_idx < len(paint_orders):
                        enhanced_data["paint_order"] = paint_orders[layout_idx]

                    client_rects_data = layout.get("clientRects", [])
                    if layout_idx < len(client_rects_data):
                        client_rect_data = client_rects_data[layout_idx]
                        if client_rect_data and len(client_rect_data) >= 4:
                            enhanced_data["client_rects"] = {
                                "x": client_rect_data[0],
                                "y": client_rect_data[1],
                                "width": client_rect_data[2],
                                "height": client_rect_data[3],
                            }

                    scroll_rects_data = layout.get("scrollRects", [])
                    if layout_idx < len(scroll_rects_data):
                        scroll_rect_data = scroll_rects_data[layout_idx]
                        if scroll_rect_data and len(scroll_rect_data) >= 4:
                            enhanced_data["scroll_rects"] = {
                                "x": scroll_rect_data[0],
                                "y": scroll_rect_data[1],
                                "width": scroll_rect_data[2],
                                "height": scroll_rect_data[3],
                            }

                    stacking_contexts = layout.get("stackingContexts", {})
                    if stacking_contexts and "index" in stacking_contexts:
                        stacking_index = stacking_contexts["index"]
                        if layout_idx < len(stacking_index):
                            enhanced_data["stacking_contexts"] = stacking_index[layout_idx]

                snapshot_lookup[snapshot_index] = enhanced_data

        return snapshot_lookup

    async def capture_raw_snapshot(
        self,
        session_id: Optional[str] = None,
    ) -> RawSnapshot:
        """
        Capture a raw DOM snapshot without enhancement processing.

        Args:
            session_id: Optional session ID for targeted snapshot

        Returns:
            Raw DOM snapshot data from CDP
        """
        try:
            params: Dict[str, Any] = {
                "computedStyles": REQUIRED_COMPUTED_STYLES,
                "includeEventListeners": True,
            }

            fut = await self.client.send(
                "DOMSnapshot.captureSnapshot",
                params=params,
                expect_result=True,
                session_id=session_id,
            )
            assert fut is not None
            msg = await fut
            raw_snapshot = msg.get("result", {})
            return raw_snapshot
        except Exception as e:
            logger.error(f"Failed to capture raw DOM snapshot: {e}")
            return {}
