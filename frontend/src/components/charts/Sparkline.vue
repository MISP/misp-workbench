<script>
export default {
  props: ["data"],
  data() {
    return {
      stroke: 3,
      width: 240, // Initial default value
      height: 96,
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
        path.push(["L", point.x, point.y].join(" ")),
      );
      return ["M" + coordinates[0].x, coordinates[0].y, ...path].join(" ");
    },
    fillEndPath() {
      return `V ${this.height} L 4 ${this.height} Z`;
    },
  },
  mounted() {
    this.observeResize();
  },
  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  },
  methods: {
    observeResize() {
      const el = this.$el.parentNode;
      this.resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          if (entry.contentRect) {
            this.width = entry.contentRect.width;
          }
        }
      });
      this.resizeObserver.observe(el);
    },
  },
};
</script>
