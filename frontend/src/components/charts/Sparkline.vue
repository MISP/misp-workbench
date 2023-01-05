<script>
export default {
    props: ["data"],
    data() {
        return {
            stroke: 3,
            width: 256,
            height: 80,
        };
    },
    computed: {
        shape() {
            const stroke = this.stroke;
            const width = this.width;
            const height = this.height - stroke * 2;
            const data = this.data || [];
            const highestPoint = Math.max.apply(null, data);
            const coordinates = [];
            const totalPoints = this.data.length - 1;
            data.forEach((item, n) => {
                const x = (n / totalPoints) * width + stroke;
                const y = height - (item / highestPoint) * height + stroke;
                coordinates.push({ x, y });
            });
            if (!coordinates[0]) {
                return (
                    "M 0 " +
                    this.stroke +
                    " L 0 " +
                    this.stroke +
                    " L " +
                    this.width +
                    " " +
                    this.stroke
                );
            }
            const path = [];
            coordinates.forEach((point) =>
                path.push(["L", point.x, point.y].join(" "))
            );
            return ["M" + coordinates[0].x, coordinates[0].y, ...path].join(" ");
        },
        fillEndPath() {
            return `V ${this.height} L 4 ${this.height} Z`;
        },
    },
};
</script>

<style>
svg {
    stroke: #1f8ceb;
    fill: rgba(31, 140, 235, 0.06);
    transition: all 1s ease-in-out;
}

svg path {
    box-sizing: border-box;
}
</style>

<template>
    <svg class="sparkline" :width="width" :height="height" :stroke-width="stroke">
        <path class="sparkline--line" :d="shape" fill="none"></path>
        <path class="sparkline--fill" :d="[shape, fillEndPath].join(' ')" stroke="none"></path>
    </svg>
</template >

