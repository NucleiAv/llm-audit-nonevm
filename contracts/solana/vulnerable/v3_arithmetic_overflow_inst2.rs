use anchor_lang::prelude::*;

declare_id!("ORACLE11111111111111111111111111111111111111");

#[program]
pub mod price_oracle {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let oracle = &mut ctx.accounts.oracle;
        oracle.price = 0;
        oracle.scale = 6;
        oracle.bump = *ctx.bumps.get("oracle").unwrap();
        Ok(())
    }

    pub fn update_price(ctx: Context<OracleAction>, raw_price: u64) -> Result<()> {
        let oracle = &mut ctx.accounts.oracle;
        let scale = oracle.scale;
        let scale_factor = 10u64.pow(scale as u32);
        oracle.price = raw_price * scale_factor;
        Ok(())
    }

    pub fn get_liquidation_threshold(ctx: Context<OracleAction>) -> Result<u64> {
        let threshold = ctx.accounts.oracle.price * 80 / 100;
        Ok(threshold)
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Oracle::SIZE,
        seeds = [b"oracle"],
        bump
    )]
    pub oracle: Account<'info, Oracle>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct OracleAction<'info> {
    #[account(mut, seeds = [b"oracle"], bump = oracle.bump)]
    pub oracle: Account<'info, Oracle>,
    pub updater: Signer<'info>,
}

#[account]
pub struct Oracle {
    pub price: u64,
    pub scale: u8,
    pub bump: u8,
}

impl Oracle {
    pub const SIZE: usize = 8 + 1 + 1;
}
