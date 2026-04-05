Shader "NeonProtocol/RaveBlacklight"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Tint", Color) = (0.05, 0.02, 0.1, 1)
        _BlacklightMap ("Blacklight Emission Map", 2D) = "black" {}
        _BlacklightColor ("Blacklight Color", Color) = (0.5, 0, 1, 1)
        _BlacklightIntensity ("Blacklight Intensity", Range(0, 10)) = 4.0
        _UVReactiveColor ("UV Reactive Accent", Color) = (0, 1, 0.5, 1)
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _NormalStrength ("Normal Strength", Range(0, 2)) = 1.0
        _BeatSpeed ("Beat Pulse Speed", Range(0, 10)) = 2.5
        _BeatIntensity ("Beat Pulse Depth", Range(0, 1)) = 0.4
        _ChromaShift ("Chromatic Shift Amount", Range(0, 0.05)) = 0.005
        _DistortionSpeed ("Distortion Speed", Float) = 1.0
        _DistortionScale ("Distortion Scale", Float) = 10.0
    }

    SubShader
    {
        Tags
        {
            "RenderType" = "Opaque"
            "RenderPipeline" = "UniversalPipeline"
            "Queue" = "Geometry"
        }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float fogFactor : TEXCOORD1;
            };

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_BlacklightMap); SAMPLER(sampler_BlacklightMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half4 _BlacklightColor;
                float _BlacklightIntensity;
                half4 _UVReactiveColor;
                float _NormalStrength;
                float _BeatSpeed;
                float _BeatIntensity;
                float _ChromaShift;
                float _DistortionSpeed;
                float _DistortionScale;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs posInputs = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = posInputs.positionCS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.fogFactor = ComputeFogFactor(posInputs.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // Beat pulse (simulates bass drops)
                float beat = 1.0 - _BeatIntensity * (sin(_Time.y * _BeatSpeed * 6.2832) * 0.5 + 0.5);

                // UV distortion (hallucinogenic warping)
                float2 distortUV = input.uv;
                distortUV.x += sin(input.uv.y * _DistortionScale + _Time.y * _DistortionSpeed) * _ChromaShift;
                distortUV.y += cos(input.uv.x * _DistortionScale + _Time.y * _DistortionSpeed) * _ChromaShift;

                // Chromatic aberration split
                half4 baseR = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, distortUV + float2(_ChromaShift, 0));
                half4 baseG = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, distortUV);
                half4 baseB = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, distortUV - float2(_ChromaShift, 0));
                half3 baseCol = half3(baseR.r, baseG.g, baseB.b) * _BaseColor.rgb;

                // Blacklight emission
                half3 blacklightTex = SAMPLE_TEXTURE2D(_BlacklightMap, sampler_BlacklightMap, input.uv).rgb;
                half3 emission = blacklightTex * _BlacklightColor.rgb * _BlacklightIntensity * beat;

                // UV-reactive accent on bright areas
                float reactivity = dot(blacklightTex, float3(0.33, 0.33, 0.33));
                emission += _UVReactiveColor.rgb * reactivity * beat * 0.5;

                half3 finalColor = baseCol + emission;
                finalColor = MixFog(finalColor, input.fogFactor);
                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Lit"
}
