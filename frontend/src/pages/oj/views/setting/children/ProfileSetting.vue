<template>
  <div class="setting-main">
    <Alert v-if="onboardingRequired" type="warning" show-icon>
      {{ $t('m.Profile_Onboarding_Notice') }}
    </Alert>
    <div class="section-title">{{$t('m.Avatar_Setting')}}</div>
    <template v-if="!avatarOption.imgSrc">
      <Upload type="drag"
              class="mini-container"
              accept=".jpg,.jpeg,.png,.bmp,.gif,.webp"
              action=""
              :before-upload="handleSelectFile">
        <div style="padding: 30px 0">
          <Icon type="ios-cloud-upload" size="52" style="color: #3399ff"></Icon>
          <p>{{ $t('m.Drop_or_Select_Avatar') }}</p>
        </div>
      </Upload>
    </template>

    <template v-else>
      <div class="flex-container">
        <div class="cropper-main inline">
          <vueCropper
            ref="cropper"
            autoCrop
            fixed
            :autoCropWidth="200"
            :autoCropHeight="200"
            :img="avatarOption.imgSrc"
            :outputSize="avatarOption.size"
            :outputType="avatarOption.outputType"
            :info="true"
            @realTime="realTime">
          </vueCropper>
        </div>
        <ButtonGroup vertical class="cropper-btn">
          <LegacyButton @click="rotate('left')">
            <Icon type="arrow-return-left" size="20"></Icon>
          </LegacyButton>
          <LegacyButton @click="rotate('right')">
            <Icon type="arrow-return-right" size="20"></Icon>
          </LegacyButton>
          <LegacyButton @click="reselect">
            <Icon type="refresh" size="20"></Icon>
          </LegacyButton>
          <LegacyButton @click="finishCrop">
            <Icon type="checkmark-round" size="20"></Icon>
          </LegacyButton>
        </ButtonGroup>
        <div class="cropper-preview" :style="previewStyle">
          <div :style=" preview.div">
            <img :src="avatarOption.imgSrc" :style="preview.img">
          </div>
        </div>
      </div>
    </template>
    <Modal v-model="uploadModalVisible"
           :title="$t('m.Upload_Avatar')">
      <div class="upload-modal">
        <p class="notice">{{ $t('m.Avatar_Will_Be_Set') }}</p>
        <img :src="uploadImgSrc"/>
      </div>
      <template #footer><div >
        <LegacyButton type="primary" @click="uploadAvatar" :loading="loadingUploadBtn">{{ $t('m.Upload') }}</LegacyButton>
      </div></template>
    </Modal>

    <div class="section-title">{{$t('m.Profile_Setting')}}</div>
    <Form ref="formProfile" :model="formProfile">
      <Row type="flex" :gutter="30" justify="space-around">
        <Col :span="11">
          <FormItem :label="$t('m.Real_Name')">
            <Input v-model="formProfile.real_name"/>
          </FormItem>
          <Form-item :label="$t('m.School')">
            <Input v-model="formProfile.school"/>
          </Form-item>
          <Form-item :label="$t('m.Major')">
            <Input v-model="formProfile.major"/>
          </Form-item>
          <FormItem :label="$t('m.Interface_Language')">
            <Select v-model="formProfile.language">
              <Option v-for="lang in languages" :key="lang.value" :value="lang.value">{{lang.label}}</Option>
            </Select>
          </FormItem>
          <Form-item>
            <LegacyButton type="primary" @click="updateProfile" :loading="loadingSaveBtn">{{ $t('m.Save_All') }}</LegacyButton>
          </Form-item>
        </Col>

        <Col :span="11">
          <Form-item :label="$t('m.Mood')">
            <Input v-model="formProfile.mood"/>
          </Form-item>
          <Form-item :label="$t('m.Blog')">
            <Input v-model="formProfile.blog"/>
          </Form-item>
          <Form-item :label="$t('m.Github')">
            <Input v-model="formProfile.github"/>
          </Form-item>
        </Col>
      </Row>
    </Form>
  </div>
</template>
<script>
  import api from '@oj/api'
  import utils from '@/utils/utils'
  import {VueCropper} from 'vue-cropper'
  import {types} from '@/store'
  import {languages} from '@/i18n'

  export default {
    components: {
      VueCropper
    },
    data () {
      return {
        loadingSaveBtn: false,
        loadingUploadBtn: false,
        uploadModalVisible: false,
        preview: {},
        uploadImgSrc: '',
        uploadBlob: null,
        avatarOption: {
          imgSrc: '',
          size: 0.86,
          outputType: 'webp'
        },
        languages: languages,
        formProfile: {
          real_name: '',
          mood: '',
          major: '',
          blog: '',
          school: '',
          github: '',
          language: ''
        }
      }
    },
    mounted () {
      let profile = this.$store.state.user.profile
      Object.keys(this.formProfile).forEach(element => {
        if (profile[element] !== undefined) {
          this.formProfile[element] = profile[element]
        }
      })
    },
    beforeUnmount () {
      this.clearUploadPreview()
    },
    methods: {
      checkFileType (file) {
        if (!/\.(gif|jpg|jpeg|png|bmp|webp)$/i.test(file.name)) {
          this.$Notice.warning({
            title: this.$t('m.Unsupported_File_Type'),
            desc: this.$t('m.Select_Image_File')
          })
          return false
        }
        return true
      },
      checkFileSize (file) {
        // The selected source may be larger; the cropped result is compressed
        // to a small WebP before it is sent to the 2 MB backend endpoint.
        if (file.size > 12 * 1024 * 1024) {
          this.$Notice.warning({
            title: this.$t('m.Image_Too_Large'),
            desc: this.$t('m.Avatar_Source_Size_Limit')
          })
          return false
        }
        return true
      },
      handleSelectFile (file) {
        this.clearUploadPreview()
        let isOk = this.checkFileType(file) && this.checkFileSize(file)
        if (!isOk) {
          return false
        }
        let reader = new window.FileReader()
        reader.onload = (e) => {
          this.avatarOption.imgSrc = e.target.result
        }
        reader.readAsDataURL(file)
        return false
      },
      realTime (data) {
        this.preview = data
      },
      rotate (direction) {
        if (direction === 'left') {
          this.$refs.cropper.rotateLeft()
        } else {
          this.$refs.cropper.rotateRight()
        }
      },
      reselect () {
        this.$Modal.confirm({
          content: this.$t('m.Discard_Avatar_Changes'),
          onOk: () => {
            this.clearUploadPreview()
            this.avatarOption.imgSrc = ''
          }
        })
      },
      finishCrop () {
        this.$refs.cropper.getCropBlob(async blob => {
          try {
            this.clearUploadPreview()
            this.uploadBlob = await this.compressAvatar(blob)
            this.uploadImgSrc = URL.createObjectURL(this.uploadBlob)
            this.uploadModalVisible = true
          } catch (_) {
            this.$error(this.$t('m.Avatar_Compression_Failed'))
          }
        })
      },
      compressAvatar (blob) {
        return new Promise((resolve, reject) => {
          const sourceUrl = URL.createObjectURL(blob)
          const image = new window.Image()
          image.onload = () => {
            const maxSide = 512
            const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight))
            const canvas = document.createElement('canvas')
            canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
            canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
            const context = canvas.getContext('2d')
            context.imageSmoothingEnabled = true
            context.imageSmoothingQuality = 'high'
            context.drawImage(image, 0, 0, canvas.width, canvas.height)
            URL.revokeObjectURL(sourceUrl)
            canvas.toBlob(result => result ? resolve(result) : reject(new Error('WebP encoding failed')), 'image/webp', 0.82)
          }
          image.onerror = () => {
            URL.revokeObjectURL(sourceUrl)
            reject(new Error('Image decoding failed'))
          }
          image.src = sourceUrl
        })
      },
      clearUploadPreview () {
        if (this.uploadImgSrc && this.uploadImgSrc.startsWith('blob:')) URL.revokeObjectURL(this.uploadImgSrc)
        this.uploadImgSrc = ''
        this.uploadBlob = null
      },
      async uploadAvatar () {
        if (!this.uploadBlob) return
        const form = new window.FormData()
        const file = new window.File([this.uploadBlob], 'avatar.webp', { type: 'image/webp' })
        form.append('image', file)
        this.loadingUploadBtn = true
        try {
          await api.uploadAvatar(form)
          await this.$store.dispatch('getProfile')
          this.$success(this.$t('m.Avatar_Updated'))
          this.uploadModalVisible = false
          this.avatarOption.imgSrc = ''
          this.clearUploadPreview()
        } finally {
          this.loadingUploadBtn = false
        }
      },
      updateProfile () {
        this.loadingSaveBtn = true
        let updateData = utils.filterEmptyValue(Object.assign({}, this.formProfile))
        api.updateProfile(updateData).then(res => {
          this.$success('Success')
          this.$store.commit(types.CHANGE_PROFILE, {profile: res.data.data})
          if (this.$route.query.onboarding === '1') {
            this.$router.replace({query: {}})
          }
          this.loadingSaveBtn = false
        }, _ => {
          this.loadingSaveBtn = false
        })
      }
    },
    computed: {
      onboardingRequired () {
        return this.$route.query.onboarding === '1' || this.$store.state.user.profile.oj_onboarding_completed === false
      },
      previewStyle () {
        return {
          'width': this.preview.w + 'px',
          'height': this.preview.h + 'px',
          'overflow': 'hidden'
        }
      }
    }
  }
</script>

<style lang="less" scoped>
  .inline {
    display: inline-block;
  }

  .copper-img {
    width: 400px;
    height: 300px;
  }

  .flex-container {
    flex-wrap: wrap;
    justify-content: flex-start;
    margin-bottom: 10px;
    .cropper-main {
      flex: none;
      .copper-img;
    }
    .cropper-btn {
      flex: none;
      vertical-align: top;
    }
    .cropper-preview {
      flex: none;
      /*margin: 10px;*/
      margin-left: 20px;
      box-shadow: 0 0 1px 0;
      .copper-img;
    }
  }

  .upload-modal {
    .notice {
      font-size: 16px;
      display: inline-block;
      vertical-align: top;
      padding: 10px;
      padding-right: 15px;
    }
    img {
      box-shadow: 0 0 1px 0;
      border-radius: 50%;
    }
  }
</style>
