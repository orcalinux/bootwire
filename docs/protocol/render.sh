#!/usr/bin/env sh
# Regenerate every SVG under image/ from the diagram sources. Run after editing any source: ./render.sh
#
#   py/bootwire_figures.py      -> layers, frames, command payloads, memory map    (Python 3, no packages)
#   dot/<kind>/*.dot       -> image/<kind>/*.svg   state machines, modules    (Graphviz)
#   puml/<kind>/*.puml     -> image/<kind>/*.svg   sequences, flowcharts      (PlantUML, needs Java)
#   py/svg_post.py         -> white background, font fallbacks and px sizes on every SVG
#
# All three share one palette: see the header of py/bootwire_figures.py and puml/_style.iuml.
set -eu
cd "$(dirname "$0")"

python3 -B py/bootwire_figures.py image

for kind in architecture states; do
  mkdir -p "image/$kind"
  for src in dot/"$kind"/*.dot; do
    dot -Tsvg "$src" -o "image/$kind/$(basename "${src%.dot}").svg"
  done
done

for kind in architecture states sequences; do
  mkdir -p "image/$kind"
  plantuml -tsvg -o "$PWD/image/$kind" puml/"$kind"/*.puml
done

python3 -B py/svg_post.py image/*/*.svg

echo "rendered: $(find image -name '*.svg' | wc -l) SVG files"
