Shader "NeonProtocol/BeastOrganic"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (0.3, 0.08, 0.15, 1)
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _NormalStrength ("Normal Strength", Range(0, 2)) = 1.5
        _EmissionMap ("Spore Emission Map", 2D) = "black" {}
        _EmissionColor ("Spore Color", Color) = (0.8, 0.1, 0.6, 1)
        _EmissionIntensity ("Emission Intensity", Range(0, 10)) = 3.0
        _PulseSpeed ("Pulse Speed", Range(0.1, 5)) = 1.2
        _PulseOffset ("Pulse UV Offset", Range(0, 1)) = 0.0
        _VeinMap ("Vein Overlay", 2D) = "black" {}
        _VeinColor ("Vein Color", Color) = (0.5, 0.02, 0.15, 1)
        _VeinPulseSpeed ("Vein Pulse Speed", Range(0, 3)) = 0.5
        _FleshDisplacement ("Flesh Displacement", Range(0, 0.1)) = 0.02
        _Smoothness ("Smoothness (Wet Surface)", Range(0, 1)) = 0.7
        _Metallic ("Metallic", Range(0, 1)) = 0.0
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
                float3 viewDirWS : TEXCOORD4;
                float fogFactor : TEXCOORD5;
            };

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_NormalMap); SAMPLER(sampler_NormalMap);
            TEXTURE2D(_EmissionMap); SAMPLER(sampler_EmissionMap);
            TEXTURE2D(_VeinMap); SAMPLER(sampler_VeinMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                float _NormalStrength;
                half4 _EmissionColor;
                float _EmissionIntensity;
                float _PulseSpeed;
                float _PulseOffset;
                half4 _VeinColor;
                float _VeinPulseSpeed;
                float _FleshDisplacement;
                float _Smoothness;
                float _Metallic;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;

                // Organic breathing displacement
                float breathe = sin(_Time.y * _PulseSpeed + input.positionOS.y * 3.0 + _PulseOffset * 6.2832) * _FleshDisplacement;
                float3 displaced = input.positionOS.xyz + input.normalOS * breathe;

                VertexPositionInputs posInputs = GetVertexPositionInputs(displaced);
                VertexNormalInputs normInputs = GetVertexNormalInputs(input.normalOS, input.tangentOS);

                output.positionCS = posInputs.positionCS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.normalWS = normInputs.normalWS;
                output.tangentWS = normInputs.tangentWS;
                output.bitangentWS = normInputs.bitangentWS;
                output.viewDirWS = GetWorldSpaceNormalizeViewDir(posInputs.positionWS);
                output.fogFactor = ComputeFogFactor(posInputs.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // Normal mapping
                half3 normalTS = UnpackNormalScale(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, input.uv), _NormalStrength);
                float3x3 TBN = float3x3(normalize(input.tangentWS), normalize(input.bitangentWS), normalize(input.normalWS));
                float3 normalWS = mul(normalTS, TBN);

                // Base color with subsurface-style tint
                half4 baseTex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                half3 baseCol = baseTex.rgb * _BaseColor.rgb;

                // Vein overlay with pulse
                half3 veinTex = SAMPLE_TEXTURE2D(_VeinMap, sampler_VeinMap, input.uv).rgb;
                float veinPulse = sin(_Time.y * _VeinPulseSpeed * 6.2832) * 0.5 + 0.5;
                baseCol = lerp(baseCol, _VeinColor.rgb, veinTex.r * veinPulse * 0.6);

                // Spore emission (pulsating bioluminescence)
                half3 emissionTex = SAMPLE_TEXTURE2D(_EmissionMap, sampler_EmissionMap, input.uv).rgb;
                float sporePulse = sin(_Time.y * _PulseSpeed * 6.2832 + emissionTex.r * 6.2832) * 0.5 + 0.5;
                half3 emission = emissionTex * _EmissionColor.rgb * _EmissionIntensity * sporePulse;

                // Simple PBR-ish lighting
                Light mainLight = GetMainLight();
                float NdotL = saturate(dot(normalWS, mainLight.direction));
                half3 diffuse = baseCol * mainLight.color * NdotL;
                half3 ambient = baseCol * 0.15;

                half3 finalColor = ambient + diffuse + emission;
                finalColor = MixFog(finalColor, input.fogFactor);
                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Lit"
}
