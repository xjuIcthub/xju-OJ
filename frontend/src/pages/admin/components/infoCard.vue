<template>
  <el-card :body-style="{padding: 0, height: '100%'}" class="info-card">
    <el-row type="flex" class="info-card-container">
      <el-col :span="8" :style="{'background-color': color}" class="height-100">
        <Icon :type="icon" :size="iconPixelSize" class="info-card-icon"></Icon>
      </el-col>
      <el-col :span="16" class="info-card-text">
        <p :style="textStyle">{{value}}</p>
        <p style="font-weight: 300;">{{message}}</p>
      </el-col>
    </el-row>
  </el-card>
</template>

<script>
  export default {
    name: 'inforCard',
    props: {
      value: [String, Number],
      color: String,
      message: String,
      icon: String,
      iconSize: {
        type: String,
        default: '35px'
      },
      countSize: {
        type: String,
        default: '25px'
      },
      countWeight: {
        type: Number,
        default: 700
      }
    },
    computed: {
      iconPixelSize () {
        return Number.parseInt(this.iconSize, 10) || 30
      },
      textStyle () {
        return {
          'font-size': this.countSize,
          'font-weight': this.countWeight,
          color: this.color
        }
      }
    }
  }
</script>

<style lang="less" scoped>
  @card-height: 90px;
  .height-100 {
    height: 100%;
  }

  .info-card {
    display: inline-block;
    margin-right: 10px;
    width: 250px;
    height: @card-height;
    text-align: center;
    vertical-align: middle;

    &-container {
      height: 100%;
      align-items: center;
      justify-content: center;
    }
    &-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: @card-height;
      color: white;
    }
    &-text {
      p {
        margin: 0;
        .minor-text {
          font-weight: 300;
          margin-top: 2px;
          font-size: 20px;
        }
      }
    }
  }
</style>
