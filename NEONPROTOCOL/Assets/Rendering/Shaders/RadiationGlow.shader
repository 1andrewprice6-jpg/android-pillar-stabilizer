Shader "NeonProtocol/RadiationGlow"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (0.5, 0.5, 0.45, 1)
        _EmissionMap ("Emission Map (Toxic Glow)", 2D) = "black" {}
        _EmissionColor ("Emission Color", Color) = (0.2, 1, 0.1, 1)
        _EmissionIntensity ("Emission Intensity", Range(0, 10)) = 3.0
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _NormalStrength ("Normal Strength", Range(0, 2)) = 1.0
        _PulseSpeed ("Pulse Speed", Range(0, 5)) = 0.8
        _PulseMin ("Pulse Min", Range(0, 1)) = 0.4
        _DesaturationAmount ("Desaturation", Range(0, 1)) = 0.5
        _ContaminationMask ("Contamination Mask", 2D) = "white" {}
        _ContaminationSpread ("Contamination Spread", Range(0, 1)) = 0.5
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
                float4 tangentOS : TANGENT;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float3 tangentWS : TEXCOORD2;
                float3 bitangentWS : TEXCOORD3;
                float fogFactor : TEXCOORD4;
            };

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_EmissionMap); SAMPLER(sampler_EmissionMap);
            TEXTURE2D(_NormalMap); SAMPLER(sampler_NormalMap);
            TEXTURE2D(_ContaminationMask); SAMPLER(sampler_ContaminationMask);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half4 _EmissionColor;
                float _EmissionIntensity;
                float _NormalStrength;
                float _PulseSpeed;
                float _PulseMin;
                float _DesaturationAmount;
                float _ContaminationSpread;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs posInputs = GetVertexPositionInputs(input.positionOS.xyz);
                VertexNormalInputs normInputs = GetVertexNormalInputs(input.normalOS, input.tangentOS);

                output.positionCS = posInputs.positionCS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.normalWS = normInputs.normalWS;
                output.tangentWS = normInputs.tangentWS;
                output.bitangentWS = normInputs.bitangentWS;
                output.fogFactor = ComputeFogFactor(posInputs.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // Sample textures
                half4 baseTex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                half3 emissionTex = SAMPLE_TEXTURE2D(_EmissionMap, sampler_EmissionMap, input.uv).rgb;
                half3 contamination = SAMPLE_TEXTURE2D(_ContaminationMask, sampler_ContaminationMask, input.uv).rgb;

                // Desaturate base to simulate post-apocalyptic bleaching
                half3 baseCol = baseTex.rgb * _BaseColor.rgb;
                float luminance = dot(baseCol, float3(0.299, 0.587, 0.114));
                baseCol = lerp(baseCol, half3(luminance, luminance, luminance), _DesaturationAmount);

                // Contamination blend (green toxic spread)
                float contaminationMask = saturate(contamination.r - (1.0 - _ContaminationSpread));
                baseCol = lerp(baseCol, baseCol * half3(0.6, 0.8, 0.4), contaminationMask * 0.5);

                // Pulsing toxic emission
                float pulse = lerp(_PulseMin, 1.0, sin(_Time.y * _PulseSpeed * 6.2832) * 0.5 + 0.5);
                half3 emission = emissionTex * _EmissionColor.rgb * _EmissionIntensity * pulse;

                half3 finalColor = baseCol + emission;
                finalColor = MixFog(finalColor, input.fogFactor);
                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Lit"
}
