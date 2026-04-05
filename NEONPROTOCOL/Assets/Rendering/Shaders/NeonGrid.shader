Shader "NeonProtocol/NeonGrid"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "black" {}
        _BaseColor ("Base Color", Color) = (0.05, 0.05, 0.08, 1)
        _GridColor ("Grid Line Color", Color) = (0, 1, 1, 1)
        _GridSpacing ("Grid Spacing", Float) = 1.0
        _GridThickness ("Grid Line Thickness", Range(0.001, 0.1)) = 0.02
        _EmissionIntensity ("Emission Intensity", Range(0, 10)) = 3.0
        _PulseSpeed ("Pulse Speed", Range(0, 5)) = 1.0
        _PulseMin ("Pulse Min Brightness", Range(0, 1)) = 0.5
        _ScrollSpeed ("Scroll Speed", Vector) = (0, 0, 0, 0)
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
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float fogFactor : TEXCOORD2;
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half4 _GridColor;
                float _GridSpacing;
                float _GridThickness;
                float _EmissionIntensity;
                float _PulseSpeed;
                float _PulseMin;
                float4 _ScrollSpeed;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs posInputs = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = posInputs.positionCS;
                output.positionWS = posInputs.positionWS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.fogFactor = ComputeFogFactor(posInputs.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // World-space grid using XZ plane
                float2 worldUV = input.positionWS.xz / _GridSpacing;
                worldUV += _ScrollSpeed.xy * _Time.y;

                // Anti-aliased grid lines via fwidth
                float2 grid = abs(frac(worldUV - 0.5) - 0.5);
                float2 fw = fwidth(worldUV);
                float2 lines = smoothstep(fw * 0.5, fw * 1.5, grid - _GridThickness);
                float gridMask = 1.0 - min(lines.x, lines.y);

                // Pulse animation
                float pulse = lerp(_PulseMin, 1.0, (sin(_Time.y * _PulseSpeed * 6.2832) * 0.5 + 0.5));

                // Base texture
                half4 baseTex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                half3 baseCol = baseTex.rgb * _BaseColor.rgb;

                // Composite: base + grid emission
                half3 emission = _GridColor.rgb * gridMask * _EmissionIntensity * pulse;
                half3 finalColor = baseCol + emission;

                finalColor = MixFog(finalColor, input.fogFactor);
                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Lit"
}
