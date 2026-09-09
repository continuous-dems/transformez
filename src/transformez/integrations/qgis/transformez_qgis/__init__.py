"""Transformez QGIS plugin entry point."""


def classFactory(iface):
    from .plugin import TransformezPlugin

    return TransformezPlugin(iface)
